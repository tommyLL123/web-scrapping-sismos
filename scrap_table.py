import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):
    # URL de la página web que contiene la tabla
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    # Realizar la solicitud HTTP a la página web
    response = requests.get(url)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la página web'
        }

    # Parsear el contenido HTML de la página web
    soup = BeautifulSoup(response.content, 'html.parser')

    # Encontrar la tabla en el HTML
    table = soup.find('table')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla en la página web'
        }

    # Extraer los encabezados de la tabla
    headers = [header.text.strip() for header in table.find_all('th')]

    # Extraer las filas de la tabla (Limitado a los últimos 10 sismos)
    rows = []
    # El índice 1:11 toma exactamente 10 elementos saltando el encabezado
    for row in table.find_all('tr')[1:11]:  
        cells = row.find_all('td')
        # Se ajusta el mapeo de columnas asegurando que no haya desbordamiento
        rows.append({headers[i]: cell.text.strip() for i, cell in enumerate(cells) if i < len(headers)})

    # Guardar los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table_db = dynamodb.Table('TablaWebScrappingSismos')

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = table_db.scan()
    with table_db.batch_writer() as batch:
        for each in scan.get('Items', []):
            batch.delete_item(
                Key={
                    'id': each['id']
                }
            )

    # Insertar los nuevos datos
    i = 1
    for row in rows:
        row['orden'] = i  # Mejor usar 'orden' que '#' para atributos de DynamoDB
        row['id'] = str(uuid.uuid4())  # Generar un ID único para cada entrada
        table_db.put_item(Item=row)
        i = i + 1

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': rows
    }