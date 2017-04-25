package main

import(
	"net/rpc"
	"fmt"
	//"net/http"
	"io/ioutil"
	"github.com/ethereum/go-ethereum/core/state"
	"log"
	"gopkg.in/urfave/cli.v1"
	"path/filepath"
	"os"
	"encoding/json"
)
type Daem int

var (
	app       *cli.App
	IPCPathFlag = cli.StringFlag{
		Name : "ipc",
		Usage : "make-up fund for sender",
		}
	SenderFlag = cli.StringFlag{
		Name : "sender",
		Usage : "make-up fund for sender",
		}
	ReceiverFlag = cli.StringFlag{
		Name : "receiver",
		Usage : "make-up fund for sender",
		}
	CodeFlag = cli.StringFlag{
		Name : "code",
		Usage : "make-up fund for sender",
		}
	ValueFlag = cli.StringFlag{
		Name : "value",
		Usage : "make-up fund for sender",
		}
	FundFlag = cli.StringFlag{
		Name : "fund",
		Usage : "make-up fund for sender",
		}
	MultisigAddressFlag = cli.StringFlag{
		Name : "multisig",
		Usage : "multisig",
		}
	InputFlag = cli.StringFlag{
		Name : "input",
		Usage : "input",
		}
	DeployFlag = cli.BoolFlag{
		Name : "deploy",
		}
	DumpFlag = cli.BoolFlag{
		Name : "dump",
	}
	WriteStateFlag = cli.StringFlag{
		Name : "writestate",
		Usage : "write the state to the account in the multisig state",
	}
	RemoveFlag = cli.BoolFlag{
		Name : "remove",
		Usage : "Remove the multisig's state",
	}
	IncNonceFlag = cli.BoolFlag{
		Name : "inc",
		Usage : "Inc the receiver's nonce",
	}
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
		SenderFlag,
		ReceiverFlag,
		MultisigAddressFlag,
		DeployFlag,
		ValueFlag,
		FundFlag,
		CodeFlag,
		InputFlag,
		DumpFlag,
		WriteStateFlag,
		RemoveFlag,
		IncNonceFlag,
		}
	app.Action = run
}

func run(ctx *cli.Context) error {
	var endpoint string
	var reply string
	if ctx.GlobalString(IPCPathFlag.Name) != "" {
		endpoint = ctx.GlobalString(IPCPathFlag.Name)
		} else {
			fmt.Println("ipc path is required")
			return nil
		}

	client, err := rpc.DialHTTP("unix", endpoint)
	if ctx.GlobalBool(RemoveFlag.Name) {
		err = client.Call("VmDaemon.RemoveStates", ctx.GlobalString(MultisigAddressFlag.Name), &reply)
		fmt.Println(reply)
		return nil
	}
	if ctx.GlobalBool(IncNonceFlag.Name) {
		command := NonceCommand{
			Multisig : ctx.GlobalString(MultisigAddressFlag.Name),
			Receiver : ctx.GlobalString(ReceiverFlag.Name),
		}
		err = client.Call("VmDaemon.IncNonce", command, &reply)
		fmt.Println(reply)
		return nil
	}
	if ctx.GlobalBool(DumpFlag.Name) {
		query := QueryRequest{
			Multisig : ctx.GlobalString(MultisigAddressFlag.Name),
			Account : ctx.GlobalString(ReceiverFlag.Name),
		}
		err = client.Call("VmDaemon.QueryStates", query, &reply)
		fmt.Println(reply)
		return nil
	}
	if ctx.GlobalString(WriteStateFlag.Name) != "" {
		f, err := ioutil.ReadFile(ctx.GlobalString(WriteStateFlag.Name))
		if err != nil {
			fmt.Println(err)
			return err
		}
		var jjson state.World
		json.Unmarshal(f,&jjson)
		writerequest := WriteCommand{
			World : jjson,
			Multisig : ctx.GlobalString(MultisigAddressFlag.Name),
		}
		err = client.Call("VmDaemon.WriteStates", writerequest, &reply)
		fmt.Println(reply)
		return nil
	}
	task := TaskCommand{
		Sender : ctx.GlobalString(SenderFlag.Name),
		Receiver : ctx.GlobalString(ReceiverFlag.Name),
		Code : ctx.GlobalString(CodeFlag.Name),
		Value : ctx.GlobalString(ValueFlag.Name),
		Fund : ctx.GlobalString(FundFlag.Name),
		Multisig : ctx.GlobalString(MultisigAddressFlag.Name),
		Deploy : ctx.GlobalBool(DeployFlag.Name),
		Input : ctx.GlobalString(InputFlag.Name),
		}
	
	if err != nil {
		log.Fatal("dialing:", err)
		}
	err = client.Call("VmDaemon.DeployContract", task, &reply)
	if err != nil {
		log.Fatal("arith error:", err)
	}
	return nil
}

func main(){

	if err := app.Run(os.Args); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
		}

}

type WriteCommand struct{
	Multisig string
	World state.World
}

type TaskCommand struct{
	Sender string
	Receiver string
	Code string
	Input string
	Value string
	Fund string
	Multisig string
	Deploy bool
}

type NonceCommand struct{
	Multisig string
	Receiver string
}

type QueryRequest struct{
	Multisig string
	Account string
}
