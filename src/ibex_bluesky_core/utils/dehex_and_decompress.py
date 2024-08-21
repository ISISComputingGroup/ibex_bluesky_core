import zlib
import binascii


def dehex_and_decompress(value: bytes) -> bytes:
    """Decompresses the inputted string, assuming it is in hex encoding.

       Args:
           value: The string to be decompressed, encoded in hex

       Returns A decompressed version of the inputted string
    """
    return zlib.decompress(binascii.unhexlify(value))
