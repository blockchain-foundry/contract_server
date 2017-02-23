pragma solidity ^0.4.7;
contract Descriptor {

	function getDescription() constant returns (bytes32){
		bytes32 somevar;
		somevar = "tencharsme";
		return somevar;
	}
}
