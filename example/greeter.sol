contract greeter
{
    address owner;
    string greeting;

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
