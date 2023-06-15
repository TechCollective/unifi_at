#!/usr/bin/env python
from pyunifi.controller import Controller
import config

c = Controller(config.UnifiHost, config.UnifiUsername, config.UnifiPassword, config.UnifiPort, "v5")

# TODO needs cleanup. Currently the admin id is hardcoded. 
# Must have it look up the ID based on a username. Probably need to demote them from Supoer Admin as well 

exception = {}

def remove_admin(exception):
    # TODO create a function to look up the Admin id from their email, then fix the for loop below to use that
    
	for site in c.get_sites():
		if site['name'] != exception:
			c.site_id = site["name"]
			params = {"admin":"640614cea685b40228d97964","cmd":"revoke-admin"}
			print(site['desc'])
			print(c._api_write("cmd/sitemgr", params=params))
   
remove_admin(exception)