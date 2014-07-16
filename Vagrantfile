# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/precise64"
  config.ssh.forward_agent = true

  config.vm.provider :virtualbox do |vb|
    vb.gui = false
    vb.customize ["modifyvm", :id, "--memory", "2048"]
    vb.customize ["modifyvm", :id, "--cpus", "2"]
  end

  config.vm.synced_folder "salt/roots/", "/srv/"
  config.vm.provision :salt do |salt|
    salt.run_highstate = true
    salt.verbose = false
    salt.minion_config = "salt/minion.conf"
  end
end
