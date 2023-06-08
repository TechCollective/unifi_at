#!/usr/bin/env python

c = Controller(config.UnifiHost, config.UnifiUsername, config.UnifiPassword, config.UnifiPort, "v5")

# TODO needs cleanup. Currently the admin id is hardcoded. 
# Must have it look up the ID based on a username. Probably need to demote them from Supoer Admin as well 

def remove_admin(exception):
	for site in c.get_sites():
		if site['name'] != exception:
			c.site_id = site["name"]
			params = {"admin":"62571624f1dce2088c222b58","cmd":"revoke-admin"}
			print(site['desc'])
			print(c._api_write("cmd/sitemgr", params=params))