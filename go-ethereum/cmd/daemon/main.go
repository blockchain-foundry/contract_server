package main

import(
	"errors"
	"fmt"
	"math/big"
	//"io/ioutil"
	//"time"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/ethdb"
	//"github.com/ethereum/go-ethereum/logger/glog"
	"strconv"
	"net/rpc"
	"os"
	//"encoding/json"
	"net/http"
	"net"
	"sync"
	"gopkg.in/urfave/cli.v1"
	"path/filepath"
)

var (

	app       *cli.App
	IPCPathFlag = cli.StringFlag{
		Name : "ipc",
		Usage : "make-up fund for sender",
		}

	StatePools map[string]*StatePool
	wg sync.WaitGroup
)

func NewApp(version, usage string) *cli.App {
	app := cli.NewApp()
	app.Name = filepath.Base(os.Args[0])
	app.Author = ""
	//app.Authors = nil
	app.Email = ""
	app.Version = version
	app.Usage = usage
	return app
}

func init() {
	app = NewApp("0.2", "the evm command line interface")
	app.Flags = []cli.Flag{
		IPCPathFlag,
		}
	app.Action = run
}

func run(ctx *cli.Context) error {
	var endpoint string
	if ctx.GlobalString(IPCPathFlag.Name) != "" {
		endpoint = ctx.GlobalString(IPCPathFlag.Name)
		} else {
			fmt.Println("Please specified the named pipe path for IPC")
			return nil
			}
	arith := new(VmDaemon)
	rpc.Register(arith)
	rpc.HandleHTTP()
	os.Remove(endpoint)
	l, e := net.Listen("unix", endpoint)
	if e != nil {
		fmt.Println("listen error:", e)
		}
	http.Serve(l, nil)

	return nil
}

func main(){
	StatePools = make(map[string]*StatePool)
	if err := app.Run(os.Args); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
		}
}

type VmDaemon int

func (self *StatePool) ExecTask(command TaskCommand) []byte{
	
	var sender, receiver vm.ContractRef

	senderadr := common.HexToAddress(command.Sender)
	if self.vmenv.state.HasAccount(senderadr) {
		sender = self.statedb.GetAccount(senderadr)
		} else {
			sender = self.statedb.CreateAccount(senderadr)
		}

	receiveradr := common.HexToAddress(command.Receiver)
	if self.vmenv.state.HasAccount(receiveradr) {
		receiver = self.statedb.GetAccount(receiveradr)
		} else {
			receiver = self.statedb.CreateAccount(receiveradr)
			}
	if command.Code != "" && receiver.GetCode() == nil{
		receiver.SetCode(common.Hex2Bytes(command.Code))
	}
	fundbalance := common.JsonToBalance([]byte(command.Fund))
	for k, v := range fundbalance{
		self.vmenv.state.AddBalance(k, sender.Address(), v)
		}
	self.vmenv.SetTime(common.Big(command.Time))
	self.vmenv.state.Commit()
	ret, err := self.vmenv.Call(
		sender,
		receiver.Address(),
		common.Hex2Bytes(command.Input),
		common.Big("10000000000"),
		common.Big("0"),
		common.JsonToBalance([]byte(command.Value)),
		)
	 
	if err != nil{
		fmt.Println(err)
		}

	if command.Deploy{
		receiver.SetCode(ret)
		}
	self.statedb.Commit()
	self.mutex.Unlock()
	return ret
}

func (t* VmDaemon) WriteStates(command WriteCommand, reply *string) error{
	states, ok := StatePools[command.Multisig]
	if !ok{
	*reply = "No stateFile"
		return errors.New("No stateFile")
	}
	states.mutex.Lock()
	ReadStateDB(states.statedb, command.World)
	states.statedb.Commit()
	states.mutex.Unlock()
	return nil
}

func (t* VmDaemon) DeployContract(command TaskCommand, result *string) error{
	var states *StatePool
	states, ok := StatePools[command.Multisig]
	if !ok {
		db, _ := ethdb.NewMemDatabase()
		statedb, _ := state.New(common.Hash{}, db)
		MyTime := common.Big(command.Time)
		env := NewEnv(statedb, vm.Config{ Debug: true}, MyTime)
		states = &StatePool{
			vmenv: env,
			statedb: statedb,
			}
		StatePools[command.Multisig] = states
	}
	if command.SyncCall {
		states.mutex.Lock()
		ret := states.ExecTask(command)
		*result = fmt.Sprintf("%x", ret)
	} else{
		go func(){
			states.mutex.Lock()
			states.ExecTask(command)
		}()
	}
	return nil
}

func (t* VmDaemon) WriteLog(command LogCommand, result *string) error{
	//write logs to a [filename]
	states, ok := StatePools[command.Multisig]
	if ok{
		f, err := os.OpenFile(command.Path, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0666)
		if err != nil {
			return err
		}
		states.statedb.Commit()
		logs := states.statedb.GcoinGetLogs()
		f.WriteString(logs)
	} else{
		return errors.New("not found")
	}
	return nil
}

func (t *VmDaemon) RemoveStates(Multisig string, result *string) error{
	states, ok := StatePools[Multisig]
	if ok {
		states.mutex.Lock()
		delete(StatePools, Multisig)
		states.mutex.Unlock()
		*result = "remove " + Multisig
		return nil
	}
	*result = "The state does not exist"
	return nil
}

func (t *VmDaemon) IncNonce(command NonceCommand, result *string) error{
	states, ok := StatePools[command.Multisig]
	if ok {
		receiveradr := common.HexToAddress(command.Receiver)
		states.mutex.Lock()
		account := states.statedb.GetStateObject(receiveradr)
		account.SetNonce(account.Nonce() + 1)
		states.statedb.Commit()
		states.mutex.Unlock()
		*result = "increase nonce of " + command.Receiver
	}else {
		*result = "cannot find states on " + command.Multisig
	}
	return nil
}

func (t *VmDaemon) QueryStates(request QueryRequest, result *string) error{
	var states *StatePool
	states, ok := StatePools[request.Multisig]
	if !ok {
		return nil
		}
	states.mutex.Lock()
	*result = string(states.statedb.Dump())
	states.mutex.Unlock()
	return nil
}


func ReadStateDB(statedb *state.StateDB,world state.World) {
	for key, value := range world.Accounts{
		address := common.HexToAddress(key)
		if !statedb.HasAccount(address) {
			statedb.CreateAccount(address)
		}
		for storage_location, storage_value := range value.Storage{
			statedb.SetState(address, common.HexToHash(storage_location), common.HexToHash(storage_value))
			}
		statedb.SetCode(address, common.Hex2Bytes(value.Code))
		stateObject := statedb.GetOrNewStateObject(address)
		for k,v := range value.Balance{
			color,_ :=strconv.Atoi(k)
			stateObject.SetBalance(uint(color), common.Big(v))
			}
		statedb.SetNonce(address, value.Nonce)
		}
}

type NonceCommand struct{
	Multisig string
	Receiver string
}
type WriteCommand struct{
	Multisig string
	World state.World
}

type QueryRequest struct{
	Multisig string
	Account string
}

type LogCommand struct{
	Multisig string
	Path string
}

type StatePool struct{
	vmenv *VMEnv
	statedb *state.StateDB
	mutex sync.Mutex
	busy bool
}

type TaskCommand struct{
	Sender string
	Input string
	Receiver string
	Code string
	Value string
	Fund string
	Multisig string
	Time string
	Deploy bool
	SyncCall bool
}

type VMEnv struct {
	state *state.StateDB
	//block *types.Block

	transactor *common.Address
	value      *big.Int

	depth int
	Gas   *big.Int
	time  *big.Int
	logs  []vm.StructLog

	evm *vm.EVM
}

func NewEnv(state *state.StateDB, cfg vm.Config, myTime *big.Int) *VMEnv {



	env := &VMEnv{
		state:      state,
		time:       myTime,
		}
	cfg.Logger.Collector = env

	env.evm = vm.New(env, cfg)
	return env
}

// ruleSet implements vm.RuleSet and will always default to the homestead rule set.
//type ruleSet struct{}

//func (ruleSet) IsHomestead(*big.Int) bool { return true }
//set all IsHomestead to be true

func (self *VMEnv) SetTime(time *big.Int) {
	self.time = time
}
func (self *VMEnv) MarkCodeHash(common.Hash)   {}
//func (self *VMEnv) RuleSet() vm.RuleSet        { return ruleSet{} }
func (self *VMEnv) Vm() vm.Vm                  { return self.evm }
func (self *VMEnv) Db() vm.Database            { return self.state }
func (self *VMEnv) MakeSnapshot() vm.Database  { return self.state.Copy() }
func (self *VMEnv) SetSnapshot(db vm.Database) { self.state.Set(db.(*state.StateDB)) }
func (self *VMEnv) Origin() common.Address     { return *self.transactor }
//func (self *VMEnv) BlockNumber() *big.Int      { return common.Big0 }
//func (self *VMEnv) Coinbase() common.Address   { return *self.transactor }
func (self *VMEnv) Time() *big.Int             { return self.time }
//func (self *VMEnv) Difficulty() *big.Int       { return common.Big1 }
//func (self *VMEnv) BlockHash() []byte          { return make([]byte, 32) }
func (self *VMEnv) Value() *big.Int            { return self.value }
func (self *VMEnv) GasLimit() *big.Int         { return big.NewInt(1000000000) }
func (self *VMEnv) VmType() vm.Type            { return vm.StdVmTy }
func (self *VMEnv) Depth() int                 { return 0 }
func (self *VMEnv) SetDepth(i int)             { self.depth = i }

func (self *VMEnv) AddStructLog(log vm.StructLog) {
	self.logs = append(self.logs, log)
}
func (self *VMEnv) StructLogs() []vm.StructLog {
	return self.logs
}
func (self *VMEnv) AddLog(log *vm.Log) {
	self.state.AddLog(log)
}
func (self *VMEnv) CanTransfer(from common.Address, balance map[uint]*big.Int) bool {
	for k,v := range balance{
		if self.state.GetBalance(k,from).Cmp(v) < 0{
			return false
			}
		}
	return true
	//return self.state.GetBalance(0,from).Cmp(balance) >= 0
}
func (self *VMEnv) Transfer(from vm.Account, to vm.Account, amount map[uint]*big.Int) {
	core.Transfer(from, to, amount)
}

func (self *VMEnv) Call(caller vm.ContractRef, addr common.Address, data []byte, gas, price *big.Int, value map[uint]*big.Int) ([]byte, error) {
	self.Gas = gas
	return core.Call(self, caller, addr, data, gas, price, value)
}

func (self *VMEnv) CallCode(caller vm.ContractRef, addr common.Address, data []byte, gas, price *big.Int, value map[uint]*big.Int) ([]byte, error) {
	return core.CallCode(self, caller, addr, data, gas, price, value)
}

func (self *VMEnv) DelegateCall(caller vm.ContractRef, addr common.Address, data []byte, gas, price *big.Int) ([]byte, error) {
	return core.DelegateCall(self, caller, addr, data, gas, price)
}

func (self *VMEnv) Create(caller vm.ContractRef, data []byte, gas, price *big.Int, value map[uint]*big.Int) ([]byte, common.Address, error) {
	return core.Create(self, caller, data, gas, price, value)
}
