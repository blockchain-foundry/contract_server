pragma solidity ^0.4.7;


/*
	The following is an extremely basic example of a solidity contract.
	It takes a string upon creation and then repeats it when greet() is called.
*/

contract greeter         // The contract definition. A constructor of the same name will be automatically called on contract creation.
{
    address owner;     // At first, an empty "address"-type variable of the name "owner". Will be set in the constructor.
    string greeting;     // At first, an empty "string"-type variable of the name "greeting". Will be set in constructor and can be changed.

    function greeter(string _greeting) public {
        owner = msg.sender;
        greeting = _greeting;
    }

    function greet() constant returns (string) {
        return greeting;
    }

    function setGreeting(string _newgreeting) public {
        greeting = _newgreeting;
    }

    function kill() {
        if (msg.sender == owner)
            suicide(owner);
    }
}
