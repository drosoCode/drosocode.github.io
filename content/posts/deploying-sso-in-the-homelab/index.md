---
title: "Depolying SSO in the homelab"
date: 2022-02-03T00:00:00+01:00
draft: true
tags:
- docker
- python
---

## OpenLDAP Configuration

## Authelia Configuration

## Services

### Services without authentication

Like static webpages, Hoppscotch, Swagger, ESP Home, Zigbee2MQTT


### Services with basic level of authentication

- Code server: add `command: --auth none` to the docker-compose file to disable built-in auth
- Jupyter: add `command: jupyter notebook --ip='*' --NotebookApp.token='' --NotebookApp.password=''` to the docker-compose file
- Hyperion-ng: go to the web ui, in Network Services, untick "Local Admin API Authentication"
- qBittorrent: if using an alternative ui (like vue-torrent) go back to the old ui, then in Settings > Web UI > Authentication, tick "Bypass authentication for clients in whitelisted IP subnets" and add  traefik's network address "10.10.0.0/16" (I also added "172.17.0.0/16" to allow direct connection from other docker services)
- Node-RED: in the "settings.js" file, comment the "adminAuth" section
- Uptime Kuma: go in the web ui, Settings > Advanced > Disable Auth

### Services with advanced authentication

#### Apache Guacamole

1st try: ldap and header auth
Add this to the env vars of the docker-compose, for guacamole (not guacd)
```yaml
LDAP_HOSTNAME: openldap
LDAP_PORT: 389
LDAP_ENCRYPTION_METHOD: none
LDAP_SEARCH_BIND_DN: cn=admin,dc=domain,dc=tld
LDAP_SEARCH_BIND_PASSWORD: BINDPASS
LDAP_USER_BASE_DN: ou=people,dc=domain,dc=tld
LDAP_USERNAME_ATTRIBUTE: uid
LDAP_MEMBER_ATTRIBUTE: member
LDAP_MEMBER_ATTRIBUTE_TYPE: dn
LDAP_GROUP_BASE_DN: ou=guacamole,dc=domain,dc=tld
LDAP_GROUP_NAME-ATTRIBUTE: cn
```

Login into guacamole using your admin account (mysql) and create groups, then in openldap, create a ou=guacamole and add a groupOfNames for each group you created in guacamole

you may have problemes with the ldap queries, to debug them, look in the logs of the openldap container.

you can test commands by going in the openldap container, and executing ldapsearch

ex: ldapsearch -x -H ldap://127.0.0.1 -D "cn=admin,dc=domain,dc=tld" -w " BINDPASS" -b "ou=guacamole,dc=domain,dc=tld" "(&(objectClass=*)(|(member=uid=thomas,ou=people,dc=domain,dc=tld)))"

```yaml
HEADER_ENABLED: 'true'
HTTP_AUTH_HEADER: Remote-User
```

but when logging in with header, no groups are present as guacamole doesn't query the ldap server cf [this](https://issues.apache.org/jira/browse/GUACAMOLE-686)

adding `MYSQL_AUTO_CREATE_ACCOUNTS: 'true'` doesn't work either, as the users are created in the database but the groups are not assigned


2nd try: OIDC

[the oidc extension doesn't send the state parameter](https://issues.apache.org/jira/browse/GUACAMOLE-560?jql=project%20%3D%20GUACAMOLE%20AND%20text%20~%20oidc)

To solve this problem you can add ``?state=1234abcedfdhf` to the authorization endpoint as pointed out by authelia's [documentation](https://www.authelia.com/integration/openid-connect/apache-guacamole/)
Then you can use the following configuration

```yaml
OPENID_AUTHORIZATION_ENDPOINT: https://auth.domain.tld/api/oidc/authorization?state=1234abcedfdhf
OPENID_JWKS_ENDPOINT: https://auth.domain.tld/api/oidc/jwks
OPENID_ISSUER: https://auth.domain.tld
OPENID_CLIENT_ID: guacamole
OPENID_REDIRECT_URI: https://guacamole.domain.tld
OPENID_SCOPE: openid email profile groups
OPENID_USERNAME_CLAIM_TYPE: preferred_username
OPENID_GROUPS_CLAIM_TYPE: groups
```

This should work for logging in but groups doesn't seem to be synced, even if this feature is supported since v1.3.0

In the end, I used the header authentication (which is faster to use at there is no redirection to the idp) with auto account creation.
```yaml
HEADER_ENABLED: 'true'
HTTP_AUTH_HEADER: Remote-User
MYSQL_AUTO_CREATE_ACCOUNTS: 'true'
```
Then I use the administrator account to manually assign groups to the users.

#### Filebrowser

Filebrowser supports header authentication

to configure it, run the container in interactive mode with you db volume mounted (without starting filebrowser, use --entrypoint=bash) and execute `./filebrowser config set --auth.method=proxy --auth.header=Remote-User`

Warning: make sure that your account exists and exactly matches you uid in openldap (filebrowser is case-sensitive)

#### Graylog

Graylog only allows for LDAP/AD and http header auth in the open source edition (sso available for [enterprise](https://docs.graylog.org/docs/openid-connect))

To configure it, go in the web ui in System > Authentication >Authenticators > Edit Authenticators > Enable single sign-on via HTTP header. Put `Remote-User` for the username header and don't forget to add the trusted_proxies option (ex: ` 172.17.0.0/16 `) in your graylog.conf file

#### LibreNMS

in your config.php file, set `$config['auth_mechanism'] = "http-auth";`

nano /opt/librenms/LibreNMS/Authentication/AuthorizerBase.php

add HTTP_REMOTE_USER

#### FreshRSS

Warning: username is case-sensitive

In config.php, add:
```php
'auth_type' => 'http_auth',
'http_auth_auto_register' => true,
```
If using the linuxserver/freshrss docker image, make sure that your image is on the latest versions.
I had to make a [PR](https://github.com/FreshRSS/FreshRSS/pull/4063) to add an auth header, as nginx prefixes some headers with HTTP_

#### Home Assistant 

Add this repo to [HACS](https://github.com/BeryJu/hass-auth-header) and install the Header Authentication integration.

In you config file:
```yaml
http:
    use_x_forwarded_for: true
    trusted_proxies:
        - 10.10.2.1/16
auth_header:
    username_header: Remote-User
```

### Services with OpenID Connect

#### Harbor

see [here](https://goharbor.io/docs/1.10/administration/configure-authentication/oidc-auth/)

add authelia rule in front of harbor to limit user authorized to login (you can only set if the user is admin or not with oidc)

All the groups returned by the oidc provider are also mapped into harbor, so you can use them to control access to projects

#### Grafana

```yaml
GF_AUTH_GENERIC_OAUTH_ENABLED: 'true'
GF_AUTH_GENERIC_OAUTH_ALLOW_SIGN_UP: 'true'
GF_AUTH_GENERIC_OAUTH_NAME: Authelia
GF_AUTH_GENERIC_OAUTH_CLIENT_ID: grafana
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET: SECRET
GF_AUTH_GENERIC_OAUTH_SCOPES: openid profile email groups
GF_AUTH_GENERIC_OAUTH_AUTH_URL: https://auth.domain.tld/api/oidc/authorize
GF_AUTH_GENERIC_OAUTH_TOKEN_URL: https://auth.domain.tld/api/oidc/token
GF_AUTH_GENERIC_OAUTH_API_URL: https://auth.domain.tld/api/oidc/userinfo
GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH: contains(groups[*], 'grafana_admin') && 'Admin' || contains(groups[*], 'grafana_editor') && 'Editor' || 'Viewer'
```

#### Proxmox

Proxmox >= 7, Datacenter -> Permissions -> Realms

```yaml
Issuer URL: https://auth.domain.tld
Realm: authelia
Client ID: proxmox
Client Key: cf secret in authelia conf
Username Claim: subject
```

https://www.authelia.com/integration/openid-connect/proxmox/

To assign admin perms: `pveum aclmod / -user thomas@authelia -roles Administrator`

#### Matrix

```yaml
oidc_providers:
  - idp_id: authelia
    idp_name: "authelia"
    issuer: "https://auth.domain.tld/"
    client_id: "matrix"
    client_secret: ""
    scopes: ["openid", "profile", "email", "groups"]
    skip_verification: true
    user_mapping_provider:
      config:
        localpart_template: "{{ user.preferred_username }}"
        display_name_template: "{{ user.name }}"
        email_template: "{{ user.email }}"
    attribute_requirements:
      - attribute: groups
        value: "matrix"
```

Note that if you already had an account, the oidc provider will re-create one.
If you want to use your old account, you can manually edit the database: in the table `user_external_ids`, change the `user_id` field to your old user id .

#### Wiki JS

```yaml
id: wikijs
description: wikijs
secret: ""
public: false
authorization_policy: two_factor
audience: []
scopes:
  - openid
  - groups
  - profile
  - email
redirect_uris:
  - https://wiki.domain.tld/login/u-u-i-d/callback
response_types:
  - code
  - id_token
response_modes:
  - form_post
userinfo_signing_algorithm: none
```

[Credits to this issue](https://github.com/authelia/authelia/issues/3148)


#### Libre NMS

create a config.php file and mount it to `/opt/librenms/config.php`

```php
$config['auth_mechanism']        = "sso";
$config['auth_logout_handler'] = 'https://auth.domain.tld/logout';
$config['sso']['mode']           = "env";
$config['sso']['create_users'] = true;
$config['sso']['update_users'] = true;
$config['sso']['user_attr'] = 'HTTP_REMOTE_USER';
$config['sso']['realname_attr'] = 'HTTP_REMOTE_NAME';
$config['sso']['email_attr'] = 'HTTP_REMOTE_EMAIL';
$config['sso']['group_attr'] = 'HTTP_REMOTE_GROUPS';
$config['sso']['group_strategy'] = 'map';
$config['sso']['group_delimiter'] = ',';
$config['sso']['group_level_map'] = ['librenms_admin' => 10];
```

#### Netbox

you can use [REMOTE_USER header](https://github.com/netbox-community/netbox/pull/4299) or [OIDC](https://github.com/netbox-community/netbox/discussions/8579)

Here, I will use the REMOTE_USER header methode which seems much easier to setup.
Just add the following env vars to your docker-compose file.

```yaml
environment:
  - REMOTE_AUTH_ENABLED=True
  - REMOTE_AUTH_HEADER=HTTP_REMOTE_USER
  - REMOTE_AUTH_BACKEND=netbox.authentication.RemoteUserBackend
  - REMOTE_AUTH_AUTO_CREATE_USER=True
  - REMOTE_AUTH_DEFAULT_GROUPS=[]
  - REMOTE_AUTH_DEFAULT_PERMISSIONS=[]
```

#### Sonarqube

We will use [this plugin](https://github.com/vaulttec/sonar-auth-oidc)

To install it, go on the sonarqube ui in Administration > Marketplace and install the plugin "OpenID Connect Authentication for SonarQube".

Then go in Administration > General > Security and under "OpenID Connect", configure your sso settings.

#### Gitea

LDAP:
  warning: use groupOfUniqueNames instead of groupOfNames to allow to use the memberOf overlay configured in the docker image [see this issue](https://github.com/osixia/docker-openldap/issues/110#issuecomment-303294386)

[see here](https://www.talkingquickly.co.uk/gitea-sso-with-keycloak-openldap-openid-connect)




ressources:
[goauthentik doc](https://goauthentik.io/integrations/services/apache-guacamole/)