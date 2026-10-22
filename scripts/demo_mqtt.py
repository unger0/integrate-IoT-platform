"""Exige pip install paho-mqtt; ponte ativada com --profile mqtt."""
from datetime import datetime,timezone
import json,uuid
import paho.mqtt.client as mqtt
client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,protocol=mqtt.MQTTv5)
client.connect('localhost',1883)
msg={'versao':'1.0','id_mensagem':str(uuid.uuid4()),'dispositivo':'ar-centro-03','tipo':'telemetria',
 'timestamp':datetime.now(timezone.utc).isoformat(), 'medidas':[{'grandeza':'pm25','valor':24.7,'unidade':'ug/m3'}]}
client.loop_start()
info=client.publish('semma/centro/ambiente/ar-centro-03/telemetria',json.dumps(msg),qos=1)
info.wait_for_publish()
client.loop_stop();client.disconnect()
print('Enviado ao broker experimental. Confirme no histórico central; ACK MQTT NÃO garante persistência no laboratório.')
