# unifi_at
Different scripts to integrate a Unifi Controller and Autotask

Must configure Autotask first. Instructions are forthcomming

ci2unifi.py - Pulls CIs from Autotask and take the hostname + description and matchs each UniFi client that it can 
with my mac address. Makes it easyer to see what you are looking in the UniFi 
Controller.

unifi2ci.py - Takes Unifi devices and make CI's for them in Autotask. This is important if you want your alerts to have the CI in the ticket.

Unifi_remove_admin.py - Begining to code a script that will remove an admin from the Unifi controller. If you have an supwer admin and you depote them to an admin, they will be an admin on all sites. The ony way to remove them is to go to each site and remove them. Or run this script.