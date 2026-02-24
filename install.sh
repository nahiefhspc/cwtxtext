#!/bin/bash
echo "-----> Installing mp4decrypt"
cd /app/bin
curl -L -o bento4.zip "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip"
unzip -o bento4.zip
cp Bento4-SDK-1-6-0-641.x86_64-unknown-linux/bin/mp4decrypt .
chmod +x mp4decrypt
rm -rf bento4.zip Bento4-SDK-1-6-0-641.x86_64-unknown-linux
echo "-----> mp4decrypt installed at /app/bin/mp4decrypt"
