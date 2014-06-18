#-------------------------------------------------------------------------------
# Name:        Connection
# Purpose:
#
# Author:      Administrator
#
# Created:     15/06/2014
# Copyright:   (c) Administrator 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import sqlobject
from sqlobject.sqlite import builder
conn = builder()('sqlobject_demo.db')


##conn = builder()(user='dbuser', passwd='dbpassword',
##                 host='localhost', db='sqlobject_demo')

def main():
    pass

if __name__ == '__main__':
    main()
