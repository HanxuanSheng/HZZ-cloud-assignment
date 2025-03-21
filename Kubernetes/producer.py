#!/usr/bin/env python
import pika
import json
import sys
import time
import os

time.sleep(60)

#params = pika.ConnectionParameters('rabbitmq-service.default.svc.cluster.local')

#connection = pika.BlockingConnection(params)
rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))

connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port))

channel = connection.channel()

channel.queue_declare(queue = 'messages', durable=True)

samples = {

    'data': {
        'list' : ['data_A','data_B','data_C','data_D'], # data is from 2016, first four periods of data taking (ABCD)
    },

    r'Background $Z,t\bar{t}$' : { # Z + ttbar
        'list' : ['Zee','Zmumu','ttbar_lep'],
        'color' : "#6b59d3" # purple
    },

    r'Background $ZZ^*$' : { # ZZ
        'list' : ['llll'],
        'color' : "#ff0000" # red
    },

    r'Signal ($m_H$ = 125 GeV)' : { # H -> ZZ -> llll
        'list' : ['ggH125_ZZ4lep','VBFH125_ZZ4lep','WH125_ZZ4lep','ZH125_ZZ4lep'],
        'color' : "#00cdff" # light blue
    },

}

def main(path):
    for s in samples: 
        for val in samples[s]['list']: 
            message =  json.dumps([path, s, val], ensure_ascii=False)
            
            channel.basic_publish(exchange='',routing_key = 'messages',body = message)
    print("All tasks have been assigned")
    connection.close()

if int(len(sys.argv)) == 2:
    main(sys.argv[1])
else:
    print("Usage: {} <path>".format(sys.argv[0]))
