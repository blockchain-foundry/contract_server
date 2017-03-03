import os, sys
sys.path.insert(0, os.path.abspath(".."))
from example.utils.encode_function_data import encode_function_data


def test_encode_function_data():
    # TEST_CASE
    # funcName: set
    # funcType: [ 'bytes32', 'address', 'bytes32' ]
    # funcParams: [ 'cepave',
    #               '0xec37d2a9cacd01ad72cfcdb5a729c833075513e8',
    #               '0x516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78' ]
    # data: 0xd79d8e6c6365706176650000000000000000000000000000000000000000000000000000000000000000000000000000ec37d2a9cacd01ad72cfcdb5a729c833075513e8516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78

    types = ['bytes32', 'address', 'bytes32']
    values = [
        'cepave',
        '0xec37d2a9cacd01ad72cfcdb5a729c833075513e8',
        '0x516d5a6e7a7641564c4e51484c785a7844534d514a72694751663752666d4b78'
    ]
    print(encode_function_data('set', types, values))

if __name__ == '__main__':
    test_encode_function_data()
