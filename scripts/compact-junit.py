import sys

from junitparser import JUnitXml, Failure


def main():
    junit_xml_file = sys.argv[1]
    suite = JUnitXml.fromfile(junit_xml_file)
    for case in suite:
        if not isinstance(case.result, Failure):
            case.system_out = ''
            case.system_err = ''
    suite.write()


if __name__ == '__main__':
    main()
