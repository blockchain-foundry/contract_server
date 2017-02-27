pragma solidity ^0.4.7;
contract mortal {
    address owner;
    int test_constractor_mortal;

    function mortal(int _test_constractor) {
      owner = msg.sender;
      test_constractor_mortal = _test_constractor;
    }
    function getStorage() constant returns (address, int) {
      return (owner, test_constractor_mortal);
    }

    function setOwner(address _address) { owner = _address; }

    function kill() { if (msg.sender == owner) selfdestruct(owner); }
}

contract greeter {
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
