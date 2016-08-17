// Copyright 2014 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// The go-ethereum library is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// The go-ethereum library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with the go-ethereum library. If not, see <http://www.gnu.org/licenses/>.

package state

import (
	"encoding/json"
	"fmt"
	"strconv"
	"github.com/ethereum/go-ethereum/common"
)

type Account struct {
	Balance  map[string]string            `json:"balance"`
	Nonce    uint64            `json:"nonce"`
	Root     string            `json:"root"`
	CodeHash string            `json:"codeHash"`
	Code     string            `json:"code"`
	Storage  map[string]string `json:"storage"`
}

type World struct {
	Root     string             `json:"root"`
	Accounts map[string]Account `json:"accounts"`
}

func (self *StateDB) RawDump() World {
	world := World{
		Root:     common.Bytes2Hex(self.trie.Root()),
		Accounts: make(map[string]Account),
	}

	it := self.trie.Iterator()
	for it.Next() {
		addr := self.trie.GetKey(it.Key)
		stateObject, err := DecodeObject(common.BytesToAddress(addr), self.db, it.Value)
		if err != nil {
			panic(err)
		}

		account := Account{
			Balance: make(map[string]string),
		//	Balance:  self.GetBalance(0,common.BytesToAddress(addr)).String(),
			Nonce:    stateObject.nonce,
			Root:     common.Bytes2Hex(stateObject.Root()),
			CodeHash: common.Bytes2Hex(stateObject.codeHash),
			Code:     common.Bytes2Hex(stateObject.Code()),
			Storage:  make(map[string]string),
		}
		balancemap := self.GetBalanceMap(common.BytesToAddress(addr))
		for k,v := range balancemap{
			account.Balance[strconv.Itoa(int(k))]=v.String()
		}
		storageIt := stateObject.trie.Iterator()
		for storageIt.Next() {
			account.Storage[common.Bytes2Hex(self.trie.GetKey(storageIt.Key))] = common.Bytes2Hex(self.GetState(common.BytesToAddress(addr),common.BytesToHash(self.trie.GetKey(storageIt.Key))).Bytes())
			// Jonah
			//
		}
		world.Accounts[common.Bytes2Hex(addr)] = account
	}
	return world
}

func (self *StateDB) Dump() []byte {
	json, err := json.MarshalIndent(self.RawDump(), "", "    ")
	if err != nil {
		fmt.Println("dump err", err)
	}

	return json
}

// Debug stuff
func (self *StateObject) CreateOutputForDiff() {
	fmt.Printf("%x %x %x %x\n", self.Address(), self.Root(), self.balance[0].Bytes(), self.nonce)
	it := self.trie.Iterator()
	for it.Next() {
		fmt.Printf("%x %x\n", it.Key, it.Value)
	}
}
