program transtechnik("P")

#include "ibexSeqPVmacros.h"
%% #include "seq_snc.h"
%% #include "epicsTime.h"
%% #include "string.h"
%% #include "math.h"
%% #include "errlog.h"
%% #include "alarm.h"

option +d;
option +r;
option +s;


PV(string, statemachine_state, "{P}STATEMACHINE:STATE", NoMon);
PV(double, inrush_wait_time, "{P}STATEMACHINE:INRUSH_WAIT", Monitor);

PV(int, curr_sp, "{P}CURR:SP:_CALC", NoMon);
PV(int, curr_sp_raw, "{P}CURR:SP:_RAW", NoMon);
PV(int, curr_sp_proccnt, "{P}CURR:SP:PROC_CNT", Monitor);

PV(int, power_sp, "{P}POWER:SP", NoMon);
PV(int, power_sp_raw, "{P}POWER:SP:_RAW", NoMon);
PV(int, power_sp_proccnt, "{P}POWER:SP:PROC_CNT", Monitor);

PV(int, reset_sp, "{P}RESET", NoMon);
PV(int, reset_sp_raw, "{P}RESET:_RAW", NoMon);
PV(int, reset_sp_proccnt, "{P}RESET:PROC_CNT", Monitor);

%{
  static const char* const PROGRAM_NAME = "transtechnik.st";
  int last_curr_sp_sent = 0;
  int last_power_sp_sent = 0;
  int last_reset_sp_sent = 0;  

  /* This needs to be a macro as the call to pvIndex has to happen from SNL code, not C code. */
  /* See https://www-csr.bessy.de/control/SoftDist/sequencer/EscapeToC.html?highlight=pvindex#calling-pv-functions-from-c */
  #define TT_TRANSITION_TO_STATE(x) tt_state_transition(ssId, pVar, pvIndex(statemachine_state), (x))
  
  static void tt_state_transition(SS_ID ssId, struct seqg_vars* const pVar, CH_ID index, const char* const new_state_name);

}%

ss transtechnik
{

  /* Initial state. */
  state initializing
  {
    entry {
      TT_TRANSITION_TO_STATE("initializing");
    }
	
    when (){} state idle
  }
  
  state idle
  {
    entry {
      TT_TRANSITION_TO_STATE("idle");
	}
	
    when(reset_sp_proccnt != last_reset_sp_sent) {} state send_reset
    when(reset_sp_proccnt == last_reset_sp_sent && power_sp_proccnt != last_power_sp_sent) {} state set_power
    when(reset_sp_proccnt == last_reset_sp_sent && power_sp_proccnt == last_power_sp_sent && curr_sp_proccnt != last_curr_sp_sent) {} state set_current
  }
  
  state set_current
  {
    entry {
	  TT_TRANSITION_TO_STATE("set_current");
	  pvGet(curr_sp);
	  PVPUT(curr_sp_raw, curr_sp);
	  last_curr_sp_sent = curr_sp_proccnt;
	}
	
	// We dont need to wait for inrush after setting a current
	when() {} state idle
  }
  
  state set_power
  {
    entry {
	  TT_TRANSITION_TO_STATE("set_power");
	  pvGet(power_sp);
	  PVPUT(power_sp_raw, power_sp);
	  last_power_sp_sent = power_sp_proccnt;
	}
	
	when() {} state wait_for_inrush
  }
  
  state send_reset
  {
    entry {
	  TT_TRANSITION_TO_STATE("send_reset");
	  pvGet(reset_sp);
	  PVPUT(reset_sp_raw, reset_sp);
	  last_reset_sp_sent = reset_sp_proccnt;
	}
	
	when() {} state wait_for_inrush
  }
  
  state wait_for_inrush
  {
    entry {
	  TT_TRANSITION_TO_STATE("wait_for_inrush");
	}
	
    when(delay(inrush_wait_time)) {} state idle
  }
}


%{
  /**
   * Called on any state transitions that occur in the state machine - primarily for debugging.
   */
  static void tt_state_transition(SS_ID ssId, struct seqg_vars* const pVar, CH_ID index, const char* const new_state_name)
  {
    strncpy(pVar->statemachine_state, new_state_name, MAX_STRING_SIZE);
	seq_pvPut(ssId, index, SYNC);
	errlogSevPrintf(errlogInfo, "%s: Entering state %s\n", PROGRAM_NAME, new_state_name);
  }
}%
