/* 
This package is made for facilitating the development of the multicurrency in the Gcoin-Smart contract project

*/
package common

import "math/big"
import "encoding/json"
import "fmt"
import "strconv"
func NewBalance(value *big.Int, color uint) map[uint]*big.Int{
	b := make(map[uint]*big.Int)
	b[color] = value
	return b
}
func BalanceCopy(balance map[uint]*big.Int) map[uint]*big.Int{
	b := make(map[uint]*big.Int)
	for k, v := range balance{
		fmt.Println("key",k,"value",v)
		b[k] = v
	}
	return b
}
func BalanceToJson(balance map[uint]*big.Int)[]byte{
	j := make(map[string]string)
	for k, v := range balance{
		fmt.Println(k,v)
		j[strconv.Itoa(int(k))] = v.String()
	}
	myjson, err := json.Marshal(j)
	if err != nil{
		fmt.Println("err",err)
	}
	fmt.Println(string(myjson))
	return myjson
}
func JsonToBalance(data []byte)map[uint]*big.Int{
	var j map[string]string
	balance := make(map[uint]*big.Int)
	json.Unmarshal(data, &j)
	for k, v := range j{
		fmt.Println(k,v)
		key, _ := strconv.Atoi(k)
		balance[uint(key)] = Big(v)
	}
	return balance
}
