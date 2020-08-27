#!/bin/env python3
import os
import sys
import stat
import json
import time
from datetime import datetime

def usage():
    print('Uage:')
    print('\t%s <block_device>' % sys.argv[0])

parameters = {}

def dump_parameters():
    with open('parameters.json', 'w') as f:
        json.dump(parameters, f)

def run_fio(fio_job, output, env):
    dump_parameters()
    for k in env.keys():
        os.putenv(k, str(env[k]))
    os.system('fio --output=%s --output-format=json %s' %
              (output, fio_job))
    print('')

def get_blkdev_size(name):
    fd = os.open(name, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)

def parse_output(output):
    with open(output, 'r') as f:
        data = json.load(f)
    return data

def discard_all(dev):
    cmd = 'blkdiscard %s' % dev
    print(cmd)
    os.system(cmd)

def run_init_write():
    run_fio('init_write.fio', 'init_write.out.json', parameters)
    time.sleep(60)

def run_rrbench(numjobs):
    global parameters

    time.sleep(10)
    jobname='rrbench'
    output = jobname + '_' + sys.argv[1].split('/')[-1] + '_' + str(numjobs) + '.out.json'
    jobfile = jobname + '.fio'

    parameters['NUMJOBS'] = numjobs
    run_fio(jobfile, output, parameters)
    data = parse_output(output)

    read_iops = -1
    # check output
    for j in data['jobs']:
        if j['error'] != 0:
            return -1
        if j['jobname'] != 'read_job':
            continue

        # check max latency <= 300 ms
        if j['read']['clat_ns']['max'] > 3*10**8:
            return -1
        # check p99.9 latency <= 50 ms
        if j['read']['clat_ns']['percentile']['99.900000'] > 5 * 10**7:
            return -1
        # check p99 latency <= 10 ms
        if j['read']['clat_ns']['percentile']['99.000000'] > 10**7:
            return -1
        read_iops = j['read']['iops']

    # print('\nsuccess with read iops %d\n' % read_iops)
    return read_iops


def system_check():
    global parameters

    if os.getuid() != 0:
        print('Please run as root')
        return False
    if len(sys.argv) < 2:
        usage()
        return False
    try:
        st = os.lstat(sys.argv[1])
    except:
        print('%s is not a block device' % sys.argv[1])
        return False

    if not stat.S_ISBLK(st.st_mode):
        print('%s is not a block device' % sys.argv[1])
        return False

    parameters['FILENAME'] = sys.argv[1]
    parameters['DEV_SIZE'] = get_blkdev_size(sys.argv[1])

    return True


def rrbench_bisect():
    global parameters

    (low, numjobs, high) = (1, 1, 1)

    parameters['FIO_RUN_TIME'] = 30

    read_iops = run_rrbench(numjobs)

    while read_iops != -1 and high < 256:
        low = high
        high *= 2
        numjobs = high

        read_iops = run_rrbench(numjobs)

    parameters['FIO_RUN_TIME'] = 60

    while high - low > 1:
        numjobs = int((high + low) / 2)
        read_iops = run_rrbench(numjobs)

        if read_iops == -1:
            high = numjobs
        else:
            low = numjobs

    parameters['FIO_RUN_TIME'] = 120
    while read_iops == -1:
        numjobs -= 1
        if numjobs == 0:
            break
        read_iops = run_rrbench(numjobs)

    if numjobs == 0:
        result_str = 'Cannot meet latency requirement\n'
    else:
        result_str = 'We get %d iops with numjobs of %d\n' % (read_iops, numjobs)
    print(result_str)
    with open('final_result.txt', 'w') as f:
        f.write(result_str)

def create_output():
    shortname = parameters['FILENAME'].split('/')[-1]
    now = datetime.now()
    out = 'outputs/' + now.strftime('%Y%m%d-%H%M%S-') + shortname
    os.makedirs(out)
    os.system('cp *.fio ' + out);
    os.chdir(out)

def main():
    if not system_check():
        sys.exit(1)

    create_output()
    discard_all(parameters['FILENAME'])
    run_init_write()
    rrbench_bisect()

if __name__ == '__main__':
    main()
