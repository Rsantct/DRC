# DRC

Genera FIRs de correción de sala DRC


## Instalación

Para **instalar** este software en el home del usuario

  ```
  cd
  wget https://github.com/Rsantct/DRC/archive/master.zip
  unzip master
  rm master.zip
  mv DRC-master DRC
  ```

Se recomienda incluir estas utilidades en el PATH del usuario:

  ```
  nano ~/bash_profile
  ```

  ```
  ### AUDIOTOOLS y DRC
  export PATH=~/bin:~/audiotools:${PATH}
  export PATH=~/bin:~/DRC/logsweep2TF:${PATH}
  export PATH=~/bin:~/DRC/drc_linpha:${PATH}
  ```

Para **actualizar** este sofware:

  ```
  sh ~/DRC/update.sh
  ```  
 
