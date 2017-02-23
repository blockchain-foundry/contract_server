pragma solidity ^0.4.7;
contract Descriptor {

	function getDescription() constant returns (bytes32){
		bytes32 somevar;
		somevar = "tencharsme";
		return somevar;
	}
}
contract Bytes32Passer {
    address creator;
    bytes savedbytes;
    bytes32 savedvar;
    string savedstring;
    Descriptor descriptor;

    event TestEvent(
        address indexed _from,
        string _savedstring
    );

    function Bytes32Passer()
    {
        creator = msg.sender;
    }

    function getDescription() returns (bytes32)
    {
      descriptor = Descriptor(DESCRIPTOR_ADDRESS);
    	savedvar = descriptor.getDescription();
    	uint8 x = 0;
    	while(x < 32)
    	{
    		savedbytes.length++;
    		savedbytes[x] = savedvar[x];
    		x++;
    	}
    	savedstring = string(savedbytes);
    	TestEvent(msg.sender, savedstring);
    	return savedvar;
    }

    function getSavedVar() constant returns (bytes32)
    {
    	return savedvar;
    }

    function getSavedBytes() constant returns (bytes)
    {
    	return savedbytes;
    }

    function getSavedString() constant returns (string)
    {
    	return savedstring;
    }
}
