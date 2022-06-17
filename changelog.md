# Changelog

**v1.8.1**  
1.Supported multiple language  
2.Improved division to support certain point for each division  
3.Removed remaining VTC-specific functions  

**v1.7.4**  
1.Added telemetry_innodb_dir config option to store telemetry table on external storage  
2.Bug fixes  

**How to enable external innodb directory on MySQL?**  
(Suppose the directory is `/var/lib/mysqlext`)  

0.Create directory, change permission
> chown mysql:mysql /var/lib/mysqlext  

1.Open `/etc/mysql/mysql.conf.d/mysqld.cnf` and add  
> innodb_directories = /var/lib/mysqlext/ # this adds the directory to known innodb directory  
  secure-file-priv = /var/lib/mysqlext/ # this allows non-root user to create table with DATA DIRECTORY

2.Grant `FILE` privilege to database user (which does not seems to be included in `ALL` privileges)

3.Reload mysqld: `systemctl restart mysql`  

4.Open `/etc/apparmor.d/usr.sbin.mysqld` and add  
> /var/lib/mysqlext/ r,  
  /var/lib/mysqlext/** rwk,
  
5.Reload apparmor: `service apparmor reload`  

**v1.7.3**  
1.Added permission control for audit log  
2.Removed non-driver (but member) from leaderboard  

**v1.7.2**  
Initial release after combing all hubs into one code  
