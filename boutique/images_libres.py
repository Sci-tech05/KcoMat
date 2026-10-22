"""
Photos libres de droits (Wikimedia Commons) choisies pour des produits du catalogue.

Chaque photo a été vérifiée visuellement (même type de produit, pas de carte d'une autre marque).
Les licences CC BY / CC BY-SA imposent de citer l'auteur : le crédit s'affiche sous la photo
sur la fiche produit (Produit.credit_image, lien vers Produit.source_image).
Import sur le serveur : `python manage.py importer_images_libres` (simulation), puis `--appliquer`.
Un produit qui a déjà une photo n'est jamais modifié.
"""

IMAGES_LIBRES = {
    'barometre-numerique-bmp280': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/BMP280Sensor.jpg/1280px-BMP280Sensor.jpg',
        'credit': 'Photo : AGermanBeck, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:BMP280Sensor.jpg',
    },
    'capteur-a-ultrasons-hc-sr04': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/HC_SR04_Ultrasonic_sensor_1480322_3_4_HDR_Enhancer.jpg/1280px-HC_SR04_Ultrasonic_sensor_1480322_3_4_HDR_Enhancer.jpg',
        'credit': 'Photo : Nevit Dilmen, CC BY-SA 3.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:HC_SR04_Ultrasonic_sensor_1480322_3_4_HDR_Enhancer.jpg',
    },
    'capteur-de-mouvement-a-micro-ondes-rcwl-0516': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/RCWL-0516_Microwave_Radar_Sensor_module_%281%29.jpg/1280px-RCWL-0516_Microwave_Radar_Sensor_module_%281%29.jpg',
        'credit': 'Photo : Suyash Dwivedi, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:RCWL-0516_Microwave_Radar_Sensor_module_(1).jpg',
    },
    'capteur-de-temperature-tmp36': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/c/c2/Temperature_Sensor_%28TMP36%29.jpg',
        'credit': 'Photo : oomlout, CC BY-SA 2.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:Temperature_Sensor_(TMP36).jpg',
    },
    'carte-esp32s': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/ESP32.jpg/1280px-ESP32.jpg',
        'credit': 'Photo : Edwiyanto, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:ESP32.jpg',
    },
    'dht22': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/AM2302_%28DHT22%29_digital_temperature_and_humidity_sensor_module.jpg/1280px-AM2302_%28DHT22%29_digital_temperature_and_humidity_sensor_module.jpg',
        'credit': 'Photo : Suyash Dwivedi, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:AM2302_(DHT22)_digital_temperature_and_humidity_sensor_module.jpg',
    },
    'ecran-lcd-20x4-i2c-bleu': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/9/98/LCD_sainsmart_LCD2004_back.png',
        'credit': 'Photo : domaine public (CC0), Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:LCD_sainsmart_LCD2004_back.png',
    },
    'ecran-lcd-20x4-i2c-vert': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/9/98/LCD_sainsmart_LCD2004_back.png',
        'credit': 'Photo : domaine public (CC0), Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:LCD_sainsmart_LCD2004_back.png',
    },
    'ecran-lcd-20x4-module-i2c': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/e/e4/LCD_sainsmart_LCD2004_front.png',
        'credit': 'Photo : domaine public (CC0), Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:LCD_sainsmart_LCD2004_front.png',
    },
    'ecran-lcd-20x4-vert': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/e/e4/LCD_sainsmart_LCD2004_front.png',
        'credit': 'Photo : domaine public (CC0), Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:LCD_sainsmart_LCD2004_front.png',
    },
    'esp32': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/ESP32.jpg/1280px-ESP32.jpg',
        'credit': 'Photo : Edwiyanto, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:ESP32.jpg',
    },
    'esp32-cam': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/ESP32-CAM.jpg/1280px-ESP32-CAM.jpg',
        'credit': 'Photo : Nowforever, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:ESP32-CAM.jpg',
    },
    'module-gsm-sim900': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/SimCom_SIM900_GSM-GPRS.jpg/1280px-SimCom_SIM900_GSM-GPRS.jpg',
        'credit': 'Photo : Aseel zm, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:SimCom_SIM900_GSM-GPRS.jpg',
    },
    'module-relais-5v-1-canal': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/SRD-05VDC-SL-C_5V_one-channel_relay_module.jpg/1280px-SRD-05VDC-SL-C_5V_one-channel_relay_module.jpg',
        'credit': 'Photo : Suyash Dwivedi, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:SRD-05VDC-SL-C_5V_one-channel_relay_module.jpg',
    },
    'nodemcu-esp8266-12': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/ESP8266_module_01.jpg/1280px-ESP8266_module_01.jpg',
        'credit': 'Photo : Suyash Dwivedi, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:ESP8266_module_01.jpg',
    },
    'nodemcu-esp8266-ch340g': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/ESP8266_module_01.jpg/1280px-ESP8266_module_01.jpg',
        'credit': 'Photo : Suyash Dwivedi, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:ESP8266_module_01.jpg',
    },
    'telecommande-ir': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Ir_mod_HX1838.jpg/1280px-Ir_mod_HX1838.jpg',
        'credit': 'Photo : Goga504, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:Ir_mod_HX1838.jpg',
    },
    'transistor-bc547': {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/BC547_Transistor_-_01.jpg',
        'credit': 'Photo : Suyash Dwivedi, CC BY-SA 4.0, Wikimedia Commons',
        'source': 'https://commons.wikimedia.org/wiki/File:BC547_Transistor_-_01.jpg',
    },
}
