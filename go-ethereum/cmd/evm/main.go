// Copyright 2014 The go-ethereum Authors
// This file is part of go-ethereum.
//
// go-ethereum is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// go-ethereum is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with go-ethereum. If not, see <http://www.gnu.org/licenses/>.

// evm executes EVM code snippets.
package main

import (
	"fmt"
	"math/big"
	"os"
	//"runtime"
//	"time"
	"io/ioutil"
	"encoding/json"
	//"strings"
	"strconv"
	//"github.com/ethereum/go-ethereum/cmd/utils"
	"path/filepath"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/core/state"
	//"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/ethdb"
	"github.com/ethereum/go-ethereum/logger/glog"
	"gopkg.in/urfave/cli.v1"
)

var (

	app       *cli.App
	FundFlag = cli.StringFlag{
		Name : "fund",
		Usage : "make-up fund for sender",
	}
	DeployFlag = cli.BoolFlag{
		Name: "deploy",
		Usage: "deploy new contract",
	}
	SenderFlag = cli.StringFlag{
		Name: "sender",
		Usage: "sender of the transaction",
	}
	ReceiverFlag = cli.StringFlag{
		Name: "receiver",
		Usage: "receiver of the transaction",
	}
	WriteFlag = cli.StringFlag{
		Name: "write",
		Usage: "wrtie states to a file",
	}
	ReadFlag = cli.StringFlag{
		Name: "read",
		Usage: "read states from a file",
	}
	DebugFlag = cli.BoolFlag{
		Name:  "debug",
		Usage: "output full trace logs",
	}
	ForceJitFlag = cli.BoolFlag{
		Name:  "forcejit",
		Usage: "forces jit compilation",
	}
	DisableJitFlag = cli.BoolFlag{
		Name:  "nojit",
		Usage: "disabled jit compilation",
	}
	CodeFlag = cli.StringFlag{
		Name:  "code",
		Usage: "EVM code",
	}
	GasFlag = cli.StringFlag{
		Name:  "gas",
		Usage: "gas limit for the evm",
		Value: "10000000000",
	}
	PriceFlag = cli.StringFlag{
		Name:  "price",
		Usage: "price set for the evm",
		Value: "0",
	}
	ValueFlag = cli.StringFlag{
		Name:  "value",
		Usage: "value set for the evm",
		Value: "0",
	}
	DumpFlag = cli.BoolFlag{
		Name:  "dump",
		Usage: "dumps the state after the run",
	}
	InputFlag = cli.StringFlag{
		Name:  "input",
		Usage: "input for the EVM",
	}
	SysStatFlag = cli.BoolFlag{
		Name:  "sysstat",
		Usage: "display system stats",
	}
	VerbosityFlag = cli.IntFlag{
		Name:  "verbosity",
		Usage: "sets the verbosity level",
	}
	CreateFlag = cli.BoolFlag{
		Name:  "create",
		Usage: "indicates the action should be create rather than call",
	}
	TimeFlag = cli.IntFlag{
		Name:  "time",
		Usage: "The current block time",
	}
	WriteLogFlag = cli.StringFlag{
		Name:  "writelog",
		Usage: "wrtie logs to a file",
	}
)



func ReadStateDB(statedb *state.StateDB,world state.World) {
	for key, value := range world.Accounts{
		//	fmt.Println("Address:",key)
		address := common.HexToAddress(key)
		statedb.CreateAccount(address)
		for storage_location, storage_value := range value.Storage{
			//		fmt.Println(common.HexToHash(storage_value),storage_value)
			statedb.SetState(address, common.HexToHash(storage_location), common.HexToHash(storage_value))
		}
		statedb.SetCode(address, common.Hex2Bytes(value.Code))
		for k,v := range value.Balance{
			color,_ :=strconv.Atoi(k)
			statedb.AddBalance(uint(color),address,common.Big(v))
		}
		statedb.SetNonce(address, value.Nonce)
	}
}


func init() {
	app = NewApp("0.2", "the evm command line interface")
	app.Flags = []cli.Flag{
		SenderFlag,
		ReceiverFlag,
		WriteFlag,
		ReadFlag,
		CreateFlag,
		DebugFlag,
		VerbosityFlag,
		ForceJitFlag,
		DisableJitFlag,
		SysStatFlag,
		CodeFlag,
		GasFlag,
		PriceFlag,
		ValueFlag,
		DumpFlag,
		InputFlag,
		DeployFlag,
		FundFlag,
		TimeFlag,
		WriteLogFlag,
	}
	app.Action = run
}
// NewApp creates an app with sane defaults.
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
func run(ctx *cli.Context) error {
	glog.SetToStderr(true)
	glog.SetV(ctx.GlobalInt(VerbosityFlag.Name))

	db, _ := ethdb.NewMemDatabase()
	statedb, _ := state.New(common.Hash{}, db)
	//fmt.Println("Sender",common.StringToAddress("sender"))
	sender := statedb.CreateAccount(common.StringToAddress("sender"))
	//morris' testing
	//get sender from outside
	if ctx.GlobalString(SenderFlag.Name) != "" {
		SenderFlagAdr := common.HexToAddress(ctx.GlobalString(SenderFlag.Name))
		if statedb.HasAccount(SenderFlagAdr) {
			sender = statedb.GetAccount(SenderFlagAdr)
		} else {
			sender = statedb.CreateAccount(SenderFlagAdr)
		}
		//fmt.Println(sender)
	}



	//MyTime := big.NewInt(time.Now().Unix())
	MyTime := big.NewInt(int64(ctx.GlobalInt(TimeFlag.Name)))
	vmenv := NewEnv(statedb, common.StringToAddress("evmuser"), common.Big(ctx.GlobalString(ValueFlag.Name)), vm.Config{
	//vmenv := NewEnv(statedb, common.Big(ctx.GlobalString(ValueFlag.Name)), vm.Config{
		Debug:     ctx.GlobalBool(DebugFlag.Name),
		ForceJit:  ctx.GlobalBool(ForceJitFlag.Name),
		EnableJit: !ctx.GlobalBool(DisableJitFlag.Name),
	}, MyTime)

	//tstart := time.Now()   removing runtime

	var (
		ret []byte
		err error
	)


	//morris' testing
	//expecting to get file name by --read [filename]
	if ctx.GlobalString(ReadFlag.Name) != "" {
		f, err := ioutil.ReadFile(ctx.GlobalString(ReadFlag.Name))
		if err != nil {
			return err
		}
		var jjson state.World
		json.Unmarshal(f,&jjson)
		ReadStateDB(statedb, jjson)
		statedb.Commit()

	}

	if ctx.GlobalBool(CreateFlag.Name) {
		input := append(common.Hex2Bytes(ctx.GlobalString(CodeFlag.Name)), common.Hex2Bytes(ctx.GlobalString(InputFlag.Name))...)
		ret, _, err = vmenv.Create(
			sender,
			input,
			common.Big(ctx.GlobalString(GasFlag.Name)),
			common.Big(ctx.GlobalString(PriceFlag.Name)),
			common.NewBalance(common.Big(ctx.GlobalString(ValueFlag.Name)),25),

		)
	} else {
		receiver := statedb.CreateAccount(common.StringToAddress("receiver"))
		//morris' testing
		//get receiver from outside
		if ctx.GlobalString(ReceiverFlag.Name) != "" {
			ReceiverFlagAdr := common.HexToAddress(ctx.GlobalString(ReceiverFlag.Name))
			if statedb.HasAccount(ReceiverFlagAdr) {
				receiver = statedb.GetAccount(ReceiverFlagAdr)
			} else {
				receiver = statedb.CreateAccount(ReceiverFlagAdr)
			}

		}
		//


		if ctx.GlobalString(CodeFlag.Name) != "" {
			receiver.SetCode(common.Hex2Bytes(ctx.GlobalString(CodeFlag.Name)))
		}

		//   adding the money to the sender
		if ctx.GlobalString(FundFlag.Name) != ""{
		//	fmt.Println(string(common.BalanceToJson(common.NewBalance(common.Big("50"),60))))
			fundbalance := common.JsonToBalance([]byte(ctx.GlobalString(FundFlag.Name)))
			for k, v := range fundbalance{
				fmt.Println(k,v)
				statedb.AddBalance(k, sender.Address(), v)
			}
		}
		//
		ret, err = vmenv.Call(
			sender,
			receiver.Address(),
			common.Hex2Bytes(ctx.GlobalString(InputFlag.Name)),
			common.Big(ctx.GlobalString(GasFlag.Name)),
			common.Big(ctx.GlobalString(PriceFlag.Name)),
			common.JsonToBalance([]byte(ctx.GlobalString(ValueFlag.Name))),
		)

		// if the deploy flag is set than create the contract.
		// run the byte code and save the output into that address.
		if ctx.GlobalBool(DeployFlag.Name) {
			receiver.SetCode(ret)
		}

	}
	//	vmdone := time.Since(tstart) removing runtime



	if ctx.GlobalBool(DumpFlag.Name) {
		statedb.Commit()
		fmt.Println("------statedb.Dump()-------")
		fmt.Println(string(statedb.Dump()))
		fmt.Println("------statedb.GcoinGetLogs()-------")
		fmt.Println(statedb.GcoinGetLogs())

	}
	vm.StdErrFormat(vmenv.StructLogs())

	if ctx.GlobalBool(SysStatFlag.Name) {
	//	var mem runtime.MemStats
	//	runtime.ReadMemStats(&mem)
	//	fmt.Printf("vm took %v\n", vmdone)
	//	fmt.Printf(`alloc:      %d
	//tot alloc:  %d
	}

	fmt.Printf("OUT: 0x%x", ret)

	if err != nil {
		fmt.Printf(" error: %v", err)
	}
	//fmt.Println()


	//morris' testing
	//write states to a [filename]
	if ctx.GlobalString(WriteFlag.Name) != "" {
		f, err := os.OpenFile(ctx.GlobalString(WriteFlag.Name), os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0666)
		if err != nil {
			return err
		}
		statedb.Commit()
		f.WriteString(string(statedb.Dump()))
		f.Close()
	}

	//write logs to a [filename]
	if ctx.GlobalString(WriteLogFlag.Name) != "" {
		f, err := os.OpenFile(ctx.GlobalString(WriteLogFlag.Name), os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0666)
		if err != nil {
			return err
		}
		statedb.Commit()
		logs := statedb.GcoinGetLogs()
		f.WriteString(logs)
	}


	return nil
}

func main() {
	if err := app.Run(os.Args); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
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

func NewEnv(state *state.StateDB, transactor common.Address, value *big.Int, cfg vm.Config, myTime *big.Int) *VMEnv {



	env := &VMEnv{
		state:      state,
		transactor: &transactor,
		value:      value,
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
/*
func (self *VMEnv) GetHash(n uint64) common.Hash {
	if self.block.Number().Cmp(big.NewInt(int64(n))) == 0 {
		return self.block.Hash()
	}
	return common.Hash{}
}
*/
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
	//	return self.state.GetBalance(0,from).Cmp(balance) >= 0
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
