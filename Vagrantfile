# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"
  config.vm.network "forwarded_port", guest: 5672, host: 5672
  config.vm.network "forwarded_port", guest: 15672, host: 15672
  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = "3072"
    vb.cpus = 2
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update && apt-get upgrade -y
    apt-get install -y docker.io python3 python3-pip
    usermod -aG docker ubuntu
    pip3 install -U pip
    pip3 install docker-compose virtualenv
  SHELL
end
