TOP=..
include $(TOP)/configure/CONFIG
#=======================================

# Install .dbd and .db files
DATA += transtechnik.proto

DB += transtechnik.db
DB += transtechnik_status_bit.db

DBD += transtechnik.dbd

LIBRARY_IOC = transtechnik
transtechnik_SRCS += transtechnik.st
transtechnik_LIBS += seq pv
transtechnik_LIBS += $(EPICS_BASE_IOC_LIBS)

#=======================================
include $(TOP)/configure/RULES
