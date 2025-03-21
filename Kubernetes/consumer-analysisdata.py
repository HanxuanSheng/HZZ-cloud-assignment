#!/usr/bin/env python
import pika
import infofile#记得dockerfile 的时候copy这个py
import numpy as np # for numerical calculations such as histogramming
import uproot # for reading .root files
import awkward as ak # to represent nested data in columnar format
import vector # for 4-momentum calculations
import json
import re
import os

MeV = 0.001
GeV = 1.0
lumi = 10
fraction = 1.0
variables = ['lep_pt','lep_eta','lep_phi','lep_E','lep_charge','lep_type']
weight_variables = ["mcWeight", "scaleFactor_PILEUP", "scaleFactor_ELE", "scaleFactor_MUON", "scaleFactor_LepTRIGGER"]

def cut_lep_type(lep_type):
    sum_lep_type = lep_type[:, 0] + lep_type[:, 1] + lep_type[:, 2] + lep_type[:, 3]
    lep_type_cut_bool = (sum_lep_type != 44) & (sum_lep_type != 48) & (sum_lep_type != 52)
    return lep_type_cut_bool # True means we should remove this entry (lepton type does not match)

# Cut lepton charge
def cut_lep_charge(lep_charge):
    # first lepton in each event is [:, 0], 2nd lepton is [:, 1] etc
    sum_lep_charge = lep_charge[:, 0] + lep_charge[:, 1] + lep_charge[:, 2] + lep_charge[:, 3] != 0
    return sum_lep_charge # True means we should remove this entry (sum of lepton charges is not equal to 0)

# Calculate invariant mass of the 4-lepton state
# [:, i] selects the i-th lepton in each event
def calc_mass(lep_pt, lep_eta, lep_phi, lep_E):
    p4 = vector.zip({"pt": lep_pt, "eta": lep_eta, "phi": lep_phi, "E": lep_E})
    invariant_mass = (p4[:, 0] + p4[:, 1] + p4[:, 2] + p4[:, 3]).M * MeV # .M calculates the invariant mass
    return invariant_mass

def calc_weight(weight_variables, sample, events):
    info = infofile.infos[sample]
    xsec_weight = (lumi*1000*info["xsec"])/(info["sumw"]*info["red_eff"]) #*1000 to go from fb-1 to pb-1
    total_weight = xsec_weight 
    for variable in weight_variables:
        total_weight = total_weight * events[variable]
    return total_weight

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', "_", filename)

def analysis_function(message):#这是大头，输入链接，返回volume里的文件。
    path = message[0]
    s = message[1]
    val = message[2]

    if s == 'data': 
        prefix = "Data/" # Data prefix
    else: # MC prefix
        prefix = "MC/mc_"+str(infofile.infos[val]["DSID"])+"."
    fileString = path+prefix+val+".4lep.root"

    tree = uproot.open(fileString)["mini"]
    #tree = tree.arrays(library="np")

    sample_data = []

    for data in tree.iterate(variables + weight_variables, 
                                 library="ak", 
                                 entry_stop=tree.num_entries*fraction, # process up to numevents*fraction
                                 step_size = 1000000): 
        nIn = len(data)#不知道计算的时候有没有用

        lep_type = data['lep_type']
        data = data[~cut_lep_type(lep_type)]
        lep_charge = data['lep_charge']
        data = data[~cut_lep_charge(lep_charge)]
            
            # Invariant Mass
        data['mass'] = calc_mass(data['lep_pt'], data['lep_eta'], data['lep_phi'], data['lep_E'])

        if 'data' not in val: # Only calculates weights if the data is MC
            data['totalWeight'] = calc_weight(weight_variables, val, data)

        sample_data.append(data)

    concatenated_data = ak.concatenate(sample_data)
    #这里加了一句
    max_len = max([
    int(ak.max(ak.num(concatenated_data[field], axis=1)).tolist())
    if concatenated_data[field].ndim > 1 else 0
    for field in concatenated_data.fields])

    concatenated_data_fixed = {}

    for field in concatenated_data.fields:
        array = concatenated_data[field]
        
        if array.ndim > 1:  # 只处理变长数组
            padded = ak.pad_none(array, max_len, clip=True)  # 填充 None
            padded = ak.fill_none(padded, np.nan)  # None -> NaN

        # 强制转换成 NumPy 兼容形状
            try:
                padded_numpy = ak.to_numpy(padded)
            except ValueError:
                print(f"Error in {field}, forcing conversion via list")
                padded_numpy = np.array(ak.to_list(padded))  # NumPy 兼容
            concatenated_data_fixed[field] = padded_numpy
        else:
            concatenated_data_fixed[field] = ak.to_numpy(array)
    
    s_name = sanitize_filename(s)      
    root_filename = f"/data/{s_name}_{val}.root"
    with uproot.recreate(root_filename) as file:
        file["data"] = concatenated_data_fixed

    print(f'{s}_{val}, analysis completed!')


#params = pika.ConnectionParameters('rabbitmq-service.default.svc.cluster.local')

#connection = pika.BlockingConnection(params)

rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))

connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port))

channel = connection.channel()

channel.queue_declare(queue = 'messages', durable=True)

def callback(ch,method,properties,body):
    message = json.loads(body)
    analysis_function(message)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue = 'messages',
                     auto_ack = False,
                     on_message_callback = callback)

channel.start_consuming()
