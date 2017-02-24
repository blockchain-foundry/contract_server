from eth_abi.abi import decode_abi, decode_single

def decodeStorageExample():
    """Examples for decode storage
    """
    # b87d8ec6e9ae49aa94bf3a041bcdd5d06ca8836e
    input = '000000000000000000000000b87d8ec6e9ae49aa94bf3a041bcdd5d06ca8836e'
    output = decode_single('address', input)
    print('[Type] address: ' + input)
    print('Decode to: ' + output + '\n')

    # gcoin
    input = '67636f696e00000000000000000000000000000000000000000000000000000a'
    output = decode_single('bytes32', input)
    print('[Type] bytes32: ' + input)
    print('Decode to: ' + output.decode('utf-8'))

    # '82a978b3f5962a5b0957d9ee9eef472ee55b42f1'
    # 1
    # b'stupid pink animal\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    # 0
    input = ('0x00000000000000000000000082a978b3f5962a5b0957d9ee9eef472ee55b42f10000000000000'
             '0000000000000000000000000000000000000000000000000017374757069642070696e6b20616e69'
             '6d616c000000000000000000000000000000000000000000000000000000000000000000000000000'
             '00000000000000000')
    output = decode_abi(['address', 'uint32', 'bytes32', 'int32'], input)
    for out in output:
        print(out)


if __name__ == '__main__':
    decodeStorageExample()
