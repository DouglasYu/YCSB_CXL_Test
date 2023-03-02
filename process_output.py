import os
import numpy as np
import pandas as pd
import argparse

PARSE_PERF = True

def parse_output(output_folder="output"):
    overall_dict = {}
    print("Processed Files:")
    for filename in os.listdir(output_folder):
        if filename[:8] != "workload": continue
        filename_ = filename[:-4].split('_')
        workload = filename_[0][8]
        node = filename_[1]
        qps = int(filename_[2][3:])
        suffix = filename_[3]
        print(workload, node, qps, suffix)
        if not (workload, node, qps) in overall_dict.keys():
            overall_dict[(workload, node, qps)] = {}

        if suffix == "Run":
            with open(os.path.join(output_folder, filename), 'r') as f:
                for line in f.readlines():
                    if "Throughput" in line:
                        ops_per_sec = float(line.split(',')[2].strip())
                        continue
                    words = line.split(',')
                    if words[0].strip() == "[READ]" and words[1].strip()[:4] == "99th":
                        read_tail_latency = words[2].strip()
                    elif words[0].strip() == "[READ-MODIFY-WRITE]" and words[1].strip()[:4] == "99th":
                    #elif words[0].strip() == "[INSERT]" and words[1].strip()[:4] == "99th":
                    #elif words[0].strip() == "[UPDATE]" and words[1].strip()[:4] == "99th":
                    # dummy
                    #elif words[0].strip() == "[CLEANUP]" and words[1].strip()[:4] == "99th":
                        update_tail_latency = words[2].strip()
            overall_dict[(workload, node, qps)]["Run"] = (read_tail_latency, update_tail_latency, ops_per_sec)

        elif suffix == "redis":
            with open(os.path.join(output_folder, filename), 'r') as f:
                redis_memory = f.readlines()[-1].strip()
                redis_memory = int(redis_memory) * 2 ** (-20)
            overall_dict[(workload, node, qps)]["redis"] = redis_memory

        elif suffix == "perf":
            perf_dict = {}
            with open(os.path.join(output_folder, filename), 'r') as f:
                for line in f.readlines()[5:9]:
                    data = line.strip().split()
                    counter = int(data[0].strip().replace(',', ''))
                    percentage = data[-1].strip('(').strip(')')
                    perf_dict[data[1].strip()] = (counter, percentage)
            overall_dict[(workload, node, qps)]["perf"] = perf_dict

    return overall_dict


def write_report(overall_dict):
    if not os.path.exists("report"):
        os.mkdir("report")
    for file, data in overall_dict.items():
        with open(os.path.join("report", "workload{}_{}_qps{}.txt".format(file[0], file[1], file[2])), 'w') as f:
            f.write("Redis Mem Size: {:.2f}GB\n".format(data["redis"]))
            f.write("99th Tail Latency: [Read] {} [UPDATE] {}\n".format(data["Run"][0], data["Run"][1]))
            f.write("Ops/sec: {:.1f}\n".format(data["Run"][2]))
            for k in data["perf"].keys():
                f.write("{} {} {}\n".format(k, data["perf"][k][0], data["perf"][k][1]))
            f.write("LLC Load Miss Rate: {:.4f}\n".format(
                data["perf"]["LLC-load-misses"][0] / data["perf"]["LLC-loads"][0]))
            f.write("LLC Write Miss Rate: {:.4f}\n".format(
                data["perf"]["LLC-store-misses"][0] / data["perf"]["LLC-stores"][0]))


def write_excel(overall_dict, filename="report.xlsx"):
    index = []
    d = {}
    if PARSE_PERF:
        d = {"Redis Mem Size": [], "Ops/sec": [], "Read": [], "Update": [], "Load Miss Rate": [], "Write Miss Rate": [],
             "Loads": [], "Load Misses": [], "Writes": [], "Write Misses": []}
    else:
        d = {"Redis Mem Size": [], "Ops/sec": [], "Read": [], "Update": []}

    for file, data in overall_dict.items():
        d["Redis Mem Size"].append(data["redis"])
        d["Ops/sec"].append(data["Run"][2])
        d["Read"].append(data["Run"][0])
        d["Update"].append(data["Run"][1])
        if PARSE_PERF:
            d["Load Miss Rate"].append(data["perf"]["LLC-load-misses"][0] / data["perf"]["LLC-loads"][0])
            d["Write Miss Rate"].append(data["perf"]["LLC-store-misses"][0] / data["perf"]["LLC-stores"][0])
            d["Loads"].append(data["perf"]["LLC-loads"][0])
            d["Load Misses"].append(data["perf"]["LLC-load-misses"][0])
            d["Writes"].append(data["perf"]["LLC-stores"][0])
            d["Write Misses"].append(data["perf"]["LLC-store-misses"][0])
        index.append(file[2])

    df = pd.DataFrame(d, index=index)
    df = df.sort_index(ascending=True)
    print(filename)
    df.to_excel(filename, sheet_name="sheet1")


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", help="The path to the output folder generated by the shell script.")
    parser.add_argument("-o", "--output_filename", help="The path to the file where the report will be generated as.")
    args = parser.parse_args()

    if args.input_folder and args.output_filename:
        overall_dict = parse_output(args.input_folder)
        # write_report(overall_dict)
        print("Report generated: ", args.output_filename)
        write_excel(overall_dict, args.output_filename)
    else:
        parser.print_help()