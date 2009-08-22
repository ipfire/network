# Some nice upstart hooks

alias halt="initctl emit --no-wait shutdown"
alias poweroff="initctl emit --no-wait shutdown"
alias reboot="initctl emit --no-wait reboot"
alias shutdown="initctl emit --no-wait shutdown"
