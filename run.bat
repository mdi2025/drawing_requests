@echo off
cd /d "%~dp0"
pythonw main.py 

CREATE TABLE `master_data_new` (
  `catalog` text,
  `revision` text,
  `item_description` text,
  `auto_id` int(11) NOT NULL AUTO_INCREMENT,
  `size` text NOT NULL,
  `qty` double(15,0) DEFAULT NULL,
  `uom` text,
  `symbol` text NOT NULL,
  `length` double(15,2) DEFAULT NULL,
  `personal_description` text,
  `item_code` text NOT NULL,
  `approved_on` text NOT NULL,
  `approved_status` text NOT NULL,
  `cust_supplied` text NOT NULL,
  `cust_code` text NOT NULL,
  `f_value` double(15,2) NOT NULL,
  `f_type` text NOT NULL,
  PRIMARY KEY (`auto_id`)
) ENGINE=MyISAM AUTO_INCREMENT=65769 DEFAULT CHARSET=latin1;