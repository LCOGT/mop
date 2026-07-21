import json
from os import path
import argparse
import glob

def compile_data(args):
    events = {}

    file_list = glob.glob(path.join(args.data_dir, 'prime*.json'))

    for file_path in file_list:
        with open(file_path,'r') as f:
            data = json.load(f)

            for name, entry in data['data'].items():
                print(name, entry)
                events[name] = [entry[4], entry[5], 'None', 'None', 'None', 'None']

    # Output to text file
    with open(args.out_file, 'w') as f:
        f.write('# Name  RA   Dec  t0[HJD]  tE[days]    u0    Ibase    Ibase_err\n')

        for name, params in events.items():
            f.write(name + ' ' + ' '.join(params) + '\n')


def get_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('data_dir', help='Path to input data directory: ')
    parser.add_argument('out_file', help='Path to output file: ')
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    args = get_args()
    compile_data(args)
