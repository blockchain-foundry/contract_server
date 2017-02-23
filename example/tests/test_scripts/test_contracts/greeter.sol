pragma solidity ^0.4.7;
contract mortal {
    address owner;

    function mortal() { owner = msg.sender; }
    function getOwner() constant returns (address) {
      return owner;
    }

    function setOwner(address _address) { owner = _address; }

    function kill() { if (msg.sender == owner) selfdestruct(owner); }
}

contract greeter is mortal {
    string greeting;

    function greeter(string _greeting) public {
        greeting = _greeting;
    }

    function greet() constant returns (string) {
        return greeting;
    }

    function setgreeter(string _greeting) public {
        greeting = _greeting;
    }
}
