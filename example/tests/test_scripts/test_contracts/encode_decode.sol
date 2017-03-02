pragma solidity ^0.4.7;
contract encodeAndDecode {
    string my_string = "init";

    bytes my_bytes;
    bytes2 my_bytes2;
    bytes32 my_bytes32;

    uint my_uint;
    int my_int;

    bool my_bool;
    address my_address;

    // array
    // output only
    address [] my_address_array_dynamic;
    int [2][2] my_int_array_2d;

    event TestEvent(
      string event_string,

      bytes  event_bytes,
      bytes2 event_bytes2,
      bytes32 indexed event_bytes32,

      uint event_uint,
      int event_int,

      bool event_bool,
      address indexed event_address,

      address [] event_address_array_dynamic,
      int [2][2] event_int_array_2d
    );

    function encodeAndDecode(string _string,
      bytes _bytes, bytes2 _bytes2, bytes32 _bytes32,
      uint _uint, int _int,
      bool _bool, address _address
       ) public {
        my_string = _string;

        my_bytes = _bytes;
        my_bytes2 = _bytes2;
        my_bytes32 = _bytes32;

        my_uint = _uint;
        my_int = _int;

        my_bool = _bool;
        my_address = _address;

        my_bytes32 = 0x1234;

        my_address_array_dynamic.push(0x0000000000000000000000000000000000000157);
        my_address_array_dynamic.push(0x0000000000000000000000000000000000000158);

        my_int_array_2d = [[1, 2],[3, 4]];
    }

    function testEvent() public {
      TestEvent(my_string,
        my_bytes, my_bytes2, my_bytes32,
        my_uint, my_int,
        my_bool, my_address,
        my_address_array_dynamic,
        my_int_array_2d);
    }


    function getAttributes() constant returns (string,
      bytes, bytes2, bytes32,
      uint,int,
      bool, address,
      address[],
      int[2][2]) {
        return (my_string,
          my_bytes, my_bytes2, my_bytes32,
          my_uint, my_int,
          my_bool, my_address,
          my_address_array_dynamic,
          my_int_array_2d);
    }
}
