#!/usr/bin/bash -ex

rm -rf /home/test_fiddler
mkdir /home/test_fiddler
cp -a test_fiddler_home/.ssh /home/test_fiddler/.ssh
cat $HOME/.ssh/id_rsa.pub >> /home/test_fiddler/.ssh/authorized_keys
chown -R test_fiddler:cfiddlers /home/test_fiddler

for i in id_rsa id_dsa config; do 
    [ -e /home/test_fiddler/.ssh/$i ] && chmod 600 /home/test_fiddler/.ssh/$id_dsa
done

for i in authorized_keys; do 
    [ -e /home/test_fiddler/.ssh/$i ] && chmod 600 /home/test_fiddler/.ssh/$id_dsa
done

chmod 700 /home/test_fiddler/.ssh




rm -rf /home/cfiddle
mkdir /home/cfiddle
chown -R cfiddle /home/cfiddle
