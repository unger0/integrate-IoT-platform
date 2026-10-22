"""Ponte experimental MQTT -> HTTP. Sem TLS/ACL nem garantia de ACK após persistência!
NÃO usar na produção nem para aceite RF-ING-01 ou RNF-10.
"""
import os,time,json
import httpx
import paho.mqtt.client as mqtt

BROKER=os.getenv('BROKER_HOST','localhost')
INGEST=os.getenv('CENTRAL_INGEST_URL','http://localhost:8000/api/v1/ingestao')
BEARER=os.getenv('IOT_LAB_MQTT_BEARER','')

def on_connect(client,userdata,flags,reason_code,properties):
    print('conectou broker',reason_code,flush=True)
    client.subscribe('+/+/+/+/telemetria',qos=1)

def on_message(client,userdata,msg):
    try:
        data=json.loads(msg.payload.decode('utf-8'))
        with httpx.Client(timeout=5) as h:
            r=h.post(INGEST,json=data,headers={'Authorization':'Bearer '+BEARER} if BEARER else {})
            print('mqtt -> http',msg.topic,r.status_code,r.text[:200],flush=True)
    except Exception as e:
        # Se HTTP falhar, esta ponte de laboratório NÃO garante reentrega: IMPLEMENTAR store-and-forward seguro.
        print('ERRO NA PONTE - mensagem pode ser perdida:',e,flush=True)

client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,protocol=mqtt.MQTTv5)
client.on_connect=on_connect;client.on_message=on_message
while True:
    try:
        client.connect(BROKER,1883,keepalive=30)
        client.loop_forever()
    except Exception as exc:
        print('broker indisponível',exc,flush=True)
        time.sleep(3)
