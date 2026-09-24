"""Independent answer checkers (see common.py for the independence rule)."""
from .common import CheckError, VERSION, packet_shape
from .families import CHECKERS


def check(packet, key):
    """Returns a report dict; status is 'pass' only if every check succeeded."""
    report = dict(id=packet['id'], family=packet['family'], checker_version=VERSION)
    try:
        if packet['id'] != key['id'] or packet['family'] != key['family']:
            raise CheckError('Packet and key do not belong together')
        if packet['family'] not in CHECKERS:
            raise CheckError('No independent checker for family ' + packet['family'])
        if not key.get('input_hashes'):
            raise CheckError('No source asset recorded in the answer key')
        packet_shape(packet)
        report.update(CHECKERS[packet['family']](packet, key))
        report['status'] = 'pass'
    except CheckError as error:
        report.update(status='fail', problem=str(error))
    except (KeyError, ValueError, IndexError, ArithmeticError) as error:
        report.update(status='fail', problem='Malformed packet or key: %s: %s' % (type(error).__name__, error))
    return report
