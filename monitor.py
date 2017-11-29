#!/usr/bin/python

import psutil, socket, time
from influxdb import InfluxDBClient
import argparse
from argparse import RawTextHelpFormatter

def observe(influx, delay):
    # CPU
    cpu_load = psutil.cpu_percent(interval=None)
    points = [{"measurement":"cpu",
                   "tags":{"core":"all",
                           "host":socket.gethostname()},
                   "fields":{"value":cpu_load}}]
    # MEM
    mem = psutil.virtual_memory()
    points.append({"measurement":"mem",
                   "tags":{"type":"used",
                           "host":socket.gethostname()},
                   "fields":{"value":mem.used}})
    points.append({"measurement":"mem",
                   "tags":{"type":"total",
                           "host":socket.gethostname()},
                   "fields":{"value":mem.total}})
    points.append({"measurement":"mem",
                   "tags":{"type":"available",
                           "host":socket.gethostname()},
                   "fields":{"value":mem.available}})
    points.append({"measurement":"mem_percent",
                   "tags":{"type":"used",
                           "host":socket.gethostname()},
                   "fields":{"value":float(mem.used) / float(mem.total)}})
    # DISK
    read_bytes = psutil.disk_io_counters().read_bytes
    write_bytes = psutil.disk_io_counters().write_bytes
    read_bytes_diff = read_bytes - observe.read_bytes
    write_bytes_diff = write_bytes - observe.write_bytes
    observe.read_bytes = read_bytes
    observe.write_bytes = write_bytes
    
    points.append({"measurement":"disk",
                   "tags":{"type":"read",
                           "host":socket.gethostname()},
                   "fields":{"value": read_bytes_diff / delay}})
    points.append({"measurement":"disk",
                   "tags":{"type":"write",
                           "host":socket.gethostname()},
                   "fields":{"value": write_bytes_diff / delay}})

    for d in psutil.disk_partitions():
        disk_space = psutil.disk_usage(d.mountpoint)
        points.append({"measurement":"disk_space",
                       "tags":{"type":"total",
                               "mountpoint":d.mountpoint,
                               "host":socket.gethostname()},
                       "fields":{"value": disk_space.total}})
        points.append({"measurement":"disk_space",
                       "tags":{"type":"used",
                               "mountpoint":d.mountpoint,
                               "host":socket.gethostname()},
                       "fields":{"value": disk_space.used}})
        points.append({"measurement":"disk_space",
                       "tags":{"type":"free",
                               "mountpoint":d.mountpoint,
                               "host":socket.gethostname()},
                       "fields":{"value": disk_space.free}})
        points.append({"measurement":"disk_space_percent",
                       "tags":{
                               "mountpoint":d.mountpoint,
                               "host":socket.gethostname()},
                       "fields":{"value": disk_space.percent}})


    # NET
    bytes_sent = psutil.net_io_counters().bytes_sent
    bytes_recv = psutil.net_io_counters().bytes_recv
    bytes_sent_diff = bytes_sent - observe.bytes_sent
    bytes_recv_diff = bytes_recv - observe.bytes_recv
    observe.bytes_sent = bytes_sent
    observe.bytes_recv = bytes_recv
    
    points.append({"measurement":"net",
                   "tags":{"type":"sent",
                           "host":socket.gethostname()},
                   "fields":{"value": bytes_sent_diff / delay}})
    points.append({"measurement":"net",
                   "tags":{"type":"recv",
                           "host":socket.gethostname()},
                   "fields":{"value": bytes_recv_diff / delay}})

    # # PROCESSES
    # nprocesses=0
    # nthreads=0
    # for proc in psutil.process_iter():
    #     try:
    #         pinfo = proc.as_dict(attrs=['pid', 'name', 'username', 'cpu_percent', 'num_threads','memory_info'])
    #         nprocesses += 1
    #         nthreads += pinfo['num_threads']
    #         points.append({"measurement":"process",
    #                        "tags":{
    #                            "pid":pinfo['pid'],
    #                            "processname":pinfo['name'],
    #                            "username":pinfo['username'],
    #                            "host":socket.gethostname()},
    #                        "fields":{"cpu_percent":pinfo['cpu_percent'],
    #                                  "num_threads":pinfo['num_threads'],
    #                                  "memory_rss":pinfo['memory_info'].rss}})
    #     except psutil.NoSuchProcess:
    #         pass

    # # NPROCSESES, NTHREADS, NCONNECTIONS, NUSERS
    # points.append({"measurement":"nprocesses",
    #                "tags":{"host":socket.gethostname()},
    #                "fields":{"value": nprocesses}})
    # points.append({"measurement":"nthreads",
    #                "tags":{"host":socket.gethostname()},
    #                "fields":{"value": nthreads}})
    # points.append({"measurement":"nconnections",
    #                "tags":{"host":socket.gethostname()},
    #                "fields":{"value": len(psutil.net_connections())}})
    # points.append({"measurement":"nusers",
    #                "tags":{"host":socket.gethostname()},
    #                "fields":{"value": len(psutil.users())}})

    # influx.query("drop series from current_process")
    # influx.query("select last(cpu_percent) as cpu_percent, processname, username, pid, memory_rss, num_threads, host into current_process from process where cpu_percent > 50 group by pid")

    influx.write_points(points)

observe.read_bytes = psutil.disk_io_counters().read_bytes
observe.write_bytes = psutil.disk_io_counters().write_bytes

observe.bytes_sent = psutil.net_io_counters().bytes_sent
observe.bytes_recv = psutil.net_io_counters().bytes_recv

def observe_per_cpu(influx):
    cpu_loads = psutil.cpu_percent(interval=1, percpu=True)
    points = []
    i = 0
    total_load = 0
    for cpu_load in cpu_loads:
        points.append({"measurement":"cpu",
                       "tags":{"core":i,
                               "host":socket.gethostname()},
                       "fields":{"value":cpu_load}})
        i += 1
        total_load += cpu_load
    points.append({"measurement":"cpu",
                   "tags":{"core":"all",
                           "host":socket.gethostname()},
                   "fields":{"value":total_load/float(i)}})
    influx.write_points(points)

def main():
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('--influx-host',
                        help='Host name of influxdb. Default value is localhost.', 
                        default='localhost')
    parser.add_argument('--influx-port', 
                        help='Port of influxdb. Default value is 8086.', 
                        type=int,
                        default=8086)
    parser.add_argument('--influx-db', 
                        help='InfluxDB Database used to write metrics. Default value is mydb.', 
                        default='monitor')
    parser.add_argument('--delay', 
                        help='Delay between two observations. Default value is 10.0.', 
                        type=float, 
                        default=10.0)
    args = parser.parse_args()

    influx_host = args.influx_host
    influx_port = args.influx_port
    influx_db = args.influx_db
    delay = args.delay

    influx = InfluxDBClient(host=influx_host, port=influx_port,database=influx_db)

    while True:
        observe(influx, delay)
        time.sleep(delay)
main()
