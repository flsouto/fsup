from os import getenv, system
import utils

system('touch token.json; chmod 777 token.json')

client_id = getenv('client_id')

url = f'https://freesound.org/apiv2/oauth2/authorize/?client_id={client_id}&response_type=code&state=x'
print(url)

system(f"brave-browser '{url}' || firefox '{url}'")
