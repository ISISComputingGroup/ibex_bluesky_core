period_settings_template = """<?xml version="1.0"?>
<Cluster>
  <Name>Hardware Periods</Name>
  <NumElts>38</NumElts>
  <EW>
    <Name>Period Setup Source</Name>
    <Choice>Use Parameters Below</Choice>
    <Choice>Read from file</Choice>
    <Val>{period_src}</Val>
  </EW>
  <EW>
    <Name>Period Type</Name>
    <Choice>Software (PC controlled)</Choice>
    <Choice>Hardware (DAE internal control)</Choice>
    <Choice>Hardware (External signal control)</Choice>
    <Val>{period_type}</Val>
  </EW>
  <String>
    <Name>Period File</Name>
    <Val>{period_file}</Val>
  </String>
  <I32>
    <Name>Number Of Software Periods</Name>
    <Val>{num_soft_periods}</Val>
  </I32>
  <DBL>
    <Name>Hardware Period Sequences</Name>
    <Val>{period_seq}</Val>
  </DBL>
  <DBL>
    <Name>Output Delay (us)</Name>
    <Val>{period_delay}</Val>
  </DBL>
  <EW>
    <Name>Type 1</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_1}</Val>
  </EW>
  <I32>
    <Name>Frames 1</Name>
    <Val>{frames_1}</Val>
  </I32>
  <U16>
    <Name>Output 1</Name>
    <Val>{output_1}</Val>
  </U16>
  <String>
    <Name>Label 1</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 2</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_2}</Val>
  </EW>
  <I32>
    <Name>Frames 2</Name>
    <Val>{frames_2}</Val>
  </I32>
  <U16>
    <Name>Output 2</Name>
    <Val>{output_2}</Val>
  </U16>
  <String>
    <Name>Label 2</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 3</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_3}</Val>
  </EW>
  <I32>
    <Name>Frames 3</Name>
    <Val>{frames_3}</Val>
  </I32>
  <U16>
    <Name>Output 3</Name>
    <Val>{output_3}</Val>
  </U16>
  <String>
    <Name>Label 3</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 4</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_4}</Val>
  </EW>
  <I32>
    <Name>Frames 4</Name>
    <Val>{frames_4}</Val>
  </I32>
  <U16>
    <Name>Output 4</Name>
    <Val>{output_4}</Val>
  </U16>
  <String>
    <Name>Label 4</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 5</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_5}</Val>
  </EW>
  <I32>
    <Name>Frames 5</Name>
    <Val>{frames_5}</Val>
  </I32>
  <U16>
    <Name>Output 5</Name>
    <Val>{output_5}</Val>
  </U16>
  <String>
    <Name>Label 5</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 6</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_6}</Val>
  </EW>
  <I32>
    <Name>Frames 6</Name>
    <Val>{frames_6}</Val>
  </I32>
  <U16>
    <Name>Output 6</Name>
    <Val>{output_6}</Val>
  </U16>
  <String>
    <Name>Label 6</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 7</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_7}</Val>
  </EW>
  <I32>
    <Name>Frames 7</Name>
    <Val>{frames_7}</Val>
  </I32>
  <U16>
    <Name>Output 7</Name>
    <Val>{output_7}</Val>
  </U16>
  <String>
    <Name>Label 7</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 8</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_8}</Val>
  </EW>
  <I32>
    <Name>Frames 8</Name>
    <Val>{frames_8}</Val>
  </I32>
  <U16>
    <Name>Output 8</Name>
    <Val>{output_8}</Val>
  </U16>
  <String>
    <Name>Label 8</Name>
    <Val/>
  </String>
</Cluster>
"""
initial_period_settings = """<?xml version="1.0"?>
<Cluster>
  <Name>Hardware Periods</Name>
  <NumElts>38</NumElts>
  <EW>
    <Name>Period Setup Source</Name>
    <Choice>Use Parameters Below</Choice>
    <Choice>Read from file</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Period Type</Name>
    <Choice>Software (PC controlled)</Choice>
    <Choice>Hardware (DAE internal control)</Choice>
    <Choice>Hardware (External signal control)</Choice>
    <Val>0</Val>
  </EW>
  <String>
    <Name>Period File</Name>
    <Val/>
  </String>
  <I32>
    <Name>Number Of Software Periods</Name>
    <Val>1</Val>
  </I32>
  <DBL>
    <Name>Hardware Period Sequences</Name>
    <Val>0</Val>
  </DBL>
  <DBL>
    <Name>Output Delay (us)</Name>
    <Val>0</Val>
  </DBL>
  <EW>
    <Name>Type 1</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 1</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 1</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 1</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 2</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 2</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 2</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 2</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 3</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 3</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 3</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 3</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 4</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 4</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 4</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 4</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 5</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 5</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 5</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 5</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 6</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 6</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 6</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 6</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 7</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 7</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 7</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 7</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 8</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 8</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 8</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 8</Name>
    <Val/>
  </String>
</Cluster>
"""

tcb_settings_template = """<Cluster>
    <Name>Time Channels</Name>
    <NumElts>123</NumElts>
    <DBL>
        <Name>TR1 From 1</Name>
        <Val>{tr1_from_1}</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 1</Name>
        <Val>{tr1_to_1}</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 1</Name>
        <Val>{tr1_steps_1}</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 1</Name>
        <Val>{tr1_mode_1}</Val>
    </U16>
    <DBL>
        <Name>TR1 From 2</Name>
        <Val>{tr1_from_2}</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 2</Name>
        <Val>{tr1_to_2}</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 2</Name>
        <Val>{tr1_steps_2}</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 2</Name>
        <Val>{tr1_mode_2}</Val>
    </U16>
    <DBL>
        <Name>TR1 From 3</Name>
        <Val>{tr1_from_3}</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 3</Name>
        <Val>{tr1_to_3}</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 3</Name>
        <Val>{tr1_steps_3}</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 3</Name>
        <Val>{tr1_mode_3}</Val>
    </U16>
    <DBL>
        <Name>TR1 From 4</Name>
        <Val>{tr1_from_4}</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 4</Name>
        <Val>{tr1_to_4}</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 4</Name>
        <Val>{tr1_steps_4}</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 4</Name>
        <Val>{tr1_mode_4}</Val>
    </U16>
    <DBL>
        <Name>TR1 From 5</Name>
        <Val>{tr1_from_5}</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 5</Name>
        <Val>{tr1_to_5}</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 5</Name>
        <Val>{tr1_steps_5}</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 5</Name>
        <Val>{tr1_mode_5}</Val>
    </U16>
    <U16>
        <Name>Time Unit</Name>
        <Val>{time_units}</Val>
    </U16>
    <String>
        <Name>Time Channel File</Name>
        <Val>{tcb_file}</Val>
    </String>
    <U16>
        <Name>Calculation Method</Name>
        <Val>{calc_method}</Val>
    </U16>
    <DBL>
        <Name>TR2 From 1</Name>
        <Val>{tr2_from_1}</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 1</Name>
        <Val>{tr2_to_1}</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 1</Name>
        <Val>{tr2_steps_1}</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 1</Name>
        <Val>{tr2_mode_1}</Val>
    </U16>
    <DBL>
        <Name>TR2 From 2</Name>
        <Val>{tr2_from_2}</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 2</Name>
        <Val>{tr2_to_2}</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 2</Name>
        <Val>{tr2_steps_2}</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 2</Name>
        <Val>{tr2_mode_2}</Val>
    </U16>
    <DBL>
        <Name>TR2 From 3</Name>
        <Val>{tr2_from_3}</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 3</Name>
        <Val>{tr2_to_3}</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 3</Name>
        <Val>{tr2_steps_3}</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 3</Name>
        <Val>{tr2_mode_3}</Val>
    </U16>
    <DBL>
        <Name>TR2 From 4</Name>
        <Val>{tr2_from_4}</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 4</Name>
        <Val>{tr2_to_4}</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 4</Name>
        <Val>{tr2_steps_4}</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 4</Name>
        <Val>{tr2_mode_4}</Val>
    </U16>
    <DBL>
        <Name>TR2 From 5</Name>
        <Val>{tr2_from_5}</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 5</Name>
        <Val>{tr2_to_5}</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 5</Name>
        <Val>{tr2_steps_5}</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 5</Name>
        <Val>{tr2_mode_5}</Val>
    </U16>
    <DBL>
        <Name>TR3 From 1</Name>
        <Val>{tr3_from_1}</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 1</Name>
        <Val>{tr3_to_1}</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 1</Name>
        <Val>{tr3_steps_1}</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 1</Name>
        <Val>{tr3_mode_1}</Val>
    </U16>
    <DBL>
        <Name>TR3 From 2</Name>
        <Val>{tr3_from_2}</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 2</Name>
        <Val>{tr3_to_2}</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 2</Name>
        <Val>{tr3_steps_2}</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 2</Name>
        <Val>{tr3_mode_2}</Val>
    </U16>
    <DBL>
        <Name>TR3 From 3</Name>
        <Val>{tr3_from_3}</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 3</Name>
        <Val>{tr3_to_3}</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 3</Name>
        <Val>{tr3_steps_3}</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 3</Name>
        <Val>{tr3_mode_3}</Val>
    </U16>
    <DBL>
        <Name>TR3 From 4</Name>
        <Val>{tr3_from_4}</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 4</Name>
        <Val>{tr3_to_4}</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 4</Name>
        <Val>{tr3_steps_4}</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 4</Name>
        <Val>{tr3_mode_4}</Val>
    </U16>
    <DBL>
        <Name>TR3 From 5</Name>
        <Val>{tr3_from_5}</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 5</Name>
        <Val>{tr3_to_5}</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 5</Name>
        <Val>{tr3_steps_5}</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 5</Name>
        <Val>{tr3_mode_5}</Val>
    </U16>
    <DBL>
        <Name>TR4 From 1</Name>
        <Val>{tr4_from_1}</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 1</Name>
        <Val>{tr4_to_1}</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 1</Name>
        <Val>{tr4_steps_1}</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 1</Name>
        <Val>{tr4_mode_1}</Val>
    </U16>
    <DBL>
        <Name>TR4 From 2</Name>
        <Val>{tr4_from_2}</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 2</Name>
        <Val>{tr4_to_2}</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 2</Name>
        <Val>{tr4_steps_2}</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 2</Name>
        <Val>{tr4_mode_2}</Val>
    </U16>
    <DBL>
        <Name>TR4 From 3</Name>
        <Val>{tr4_from_3}</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 3</Name>
        <Val>{tr4_to_3}</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 3</Name>
        <Val>{tr4_steps_3}</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 3</Name>
        <Val>{tr4_mode_3}</Val>
    </U16>
    <DBL>
        <Name>TR4 From 4</Name>
        <Val>{tr4_from_4}</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 4</Name>
        <Val>{tr4_to_4}</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 4</Name>
        <Val>{tr4_steps_4}</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 4</Name>
        <Val>{tr4_mode_4}</Val>
    </U16>
    <DBL>
        <Name>TR4 From 5</Name>
        <Val>{tr4_from_5}</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 5</Name>
        <Val>{tr4_to_5}</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 5</Name>
        <Val>{tr4_steps_5}</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 5</Name>
        <Val>{tr4_mode_5}</Val>
    </U16>
    <DBL>
        <Name>TR5 From 1</Name>
        <Val>{tr5_from_1}</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 1</Name>
        <Val>{tr5_to_1}</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 1</Name>
        <Val>{tr5_steps_1}</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 1</Name>
        <Val>{tr5_mode_1}</Val>
    </U16>
    <DBL>
        <Name>TR5 From 2</Name>
        <Val>{tr5_from_2}</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 2</Name>
        <Val>{tr5_to_2}</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 2</Name>
        <Val>{tr5_steps_2}</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 2</Name>
        <Val>{tr5_mode_2}</Val>
    </U16>
    <DBL>
        <Name>TR5 From 3</Name>
        <Val>{tr5_from_3}</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 3</Name>
        <Val>{tr5_to_3}</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 3</Name>
        <Val>{tr5_steps_3}</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 3</Name>
        <Val>{tr5_mode_3}</Val>
    </U16>
    <DBL>
        <Name>TR5 From 4</Name>
        <Val>{tr5_from_4}</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 4</Name>
        <Val>{tr5_to_4}</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 4</Name>
        <Val>{tr5_steps_4}</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 4</Name>
        <Val>{tr5_mode_4}</Val>
    </U16>
    <DBL>
        <Name>TR5 From 5</Name>
        <Val>{tr5_from_5}</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 5</Name>
        <Val>{tr5_to_5}</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 5</Name>
        <Val>{tr5_steps_5}</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 5</Name>
        <Val>{tr5_mode_5}</Val>
    </U16>
    <DBL>
        <Name>TR6 From 1</Name>
        <Val>{tr6_from_1}</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 1</Name>
        <Val>{tr6_to_1}</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 1</Name>
        <Val>{tr6_steps_1}</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 1</Name>
        <Val>{tr6_mode_1}</Val>
    </U16>
    <DBL>
        <Name>TR6 From 2</Name>
        <Val>{tr6_from_2}</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 2</Name>
        <Val>{tr6_to_2}</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 2</Name>
        <Val>{tr6_steps_2}</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 2</Name>
        <Val>{tr6_mode_2}</Val>
    </U16>
    <DBL>
        <Name>TR6 From 3</Name>
        <Val>{tr6_from_3}</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 3</Name>
        <Val>{tr6_to_3}</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 3</Name>
        <Val>{tr6_steps_3}</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 3</Name>
        <Val>{tr6_mode_3}</Val>
    </U16>
    <DBL>
        <Name>TR6 From 4</Name>
        <Val>{tr6_from_4}</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 4</Name>
        <Val>{tr6_to_4}</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 4</Name>
        <Val>{tr6_steps_4}</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 4</Name>
        <Val>{tr6_mode_4}</Val>
    </U16>
    <DBL>
        <Name>TR6 From 5</Name>
        <Val>{tr6_from_5}</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 5</Name>
        <Val>{tr6_to_5}</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 5</Name>
        <Val>{tr6_steps_5}</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 5</Name>
        <Val>{tr6_mode_5}</Val>
    </U16>
</Cluster>
"""
initial_tcb_settings = """<Cluster>
    <Name>Time Channels</Name>
    <NumElts>123</NumElts>
    <DBL>
        <Name>TR1 From 1</Name>
        <Val>150</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 1</Name>
        <Val>95000</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 1</Name>
        <Val>0.002</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 1</Name>
        <Val>2</Val>
    </U16>
    <DBL>
        <Name>TR1 From 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 2</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 2</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR1 From 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 3</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 3</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR1 From 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 4</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 4</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR1 From 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 To 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR1 Steps 5</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR1 In Mode 5</Name>
        <Val>0</Val>
    </U16>
    <U16>
        <Name>Time Unit</Name>
        <Val>0</Val>
    </U16>
    <String>
        <Name>Time Channel File</Name>
        <Val></Val>
    </String>
    <U16>
        <Name>Calculation Method</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR2 From 1</Name>
        <Val>150</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 1</Name>
        <Val>95000</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 1</Name>
        <Val>1.5</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 1</Name>
        <Val>1</Val>
    </U16>
    <DBL>
        <Name>TR2 From 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 2</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 2</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR2 From 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 3</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 3</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR2 From 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 4</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 4</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR2 From 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 To 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR2 Steps 5</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR2 In Mode 5</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR3 From 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 1</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 1</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR3 From 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 2</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 2</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR3 From 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 3</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 3</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR3 From 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 4</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 4</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR3 From 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 To 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR3 Steps 5</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR3 In Mode 5</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR4 From 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 1</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 1</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR4 From 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 2</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 2</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR4 From 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 3</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 3</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR4 From 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 4</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 4</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR4 From 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 To 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR4 Steps 5</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR4 In Mode 5</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR5 From 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 1</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 1</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR5 From 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 2</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 2</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR5 From 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 3</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 3</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR5 From 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 4</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 4</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR5 From 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 To 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR5 Steps 5</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR5 In Mode 5</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR6 From 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 1</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 1</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 1</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR6 From 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 2</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 2</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 2</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR6 From 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 3</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 3</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 3</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR6 From 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 4</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 4</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 4</Name>
        <Val>0</Val>
    </U16>
    <DBL>
        <Name>TR6 From 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 To 5</Name>
        <Val>0</Val>
    </DBL>
    <DBL>
        <Name>TR6 Steps 5</Name>
        <Val>0</Val>
    </DBL>
    <U16>
        <Name>TR6 In Mode 5</Name>
        <Val>0</Val>
    </U16>
</Cluster>
"""

dae_settings_template = """<?xml version="1.0"?>
<Cluster>
  <Name>Data Acquisition</Name>
  <NumElts>23</NumElts>
  <I32>
    <Name>Monitor Spectrum</Name>
    <Val>{mon_spec}</Val>
  </I32>
  <DBL>
    <Name>from</Name>
    <Val>{from_}</Val>
  </DBL>
  <DBL>
    <Name>to</Name>
    <Val>{to}</Val>
  </DBL>
  <String>
    <Name>Wiring Table</Name>
    <Val>{wiring_table}</Val>
  </String>
  <String>
    <Name>Detector Table</Name>
    <Val>{detector_table}</Val>
  </String>
  <String>
    <Name>Spectra Table</Name>
    <Val>{spectra_table}</Val>
  </String>
  <EW>
    <Name>DAETimingSource</Name>
    <Choice>ISIS</Choice>
    <Choice>Internal Test Clock</Choice>
    <Choice>SMP</Choice>
    <Choice>Muon Cerenkov</Choice>
    <Choice>Muon MS</Choice>
    <Choice>ISIS (first TS1)</Choice>
    <Choice>TS1 Only</Choice>
    <Val>{timing_src}</Val>
  </EW>
  <EW>
    <Name>SMP (Chopper) Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{smp_veto}</Val>
  </EW>
  <EW>
    <Name>Veto 0</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_0}</Val>
  </EW>
  <EW>
    <Name>Muon MS Mode</Name>
    <Choice>DISABLED</Choice>
    <Choice>ENABLED</Choice>
    <Val>{muon_ms_mode}</Val>
  </EW>
  <EW>
    <Name> Fermi Chopper Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{fermi_veto}</Val>
  </EW>
  <DBL>
    <Name>FC Delay</Name>
    <Val>{fc_delay}</Val>
  </DBL>
  <DBL>
    <Name>FC Width</Name>
    <Val>{fc_width}</Val>
  </DBL>
  <EW>
    <Name>Veto 1</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_1}</Val>
  </EW>
  <EW>
    <Name>Veto 2</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_2}</Val>
  </EW>
  <EW>
    <Name>Veto 3</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_3}</Val>
  </EW>
  <EW>
    <Name>Muon Cerenkov Pulse</Name>
    <Choice>FIRST</Choice>
    <Choice>SECOND</Choice>
    <Val>{muon_cherenkov_pulse}</Val>
  </EW>
  <EW>
    <Name> TS2 Pulse Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{ts2_veto}</Val>
  </EW>
  <EW>
    <Name> ISIS 50Hz Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{hz50_veto}</Val>
  </EW>
  <String>
    <Name>Veto 0 Name</Name>
    <Val>{veto_0_name}</Val>
  </String>
  <String>
    <Name>Veto 1 Name</Name>
    <Val>{veto_1_name}</Val>
  </String>
  <String>
    <Name>Veto 2 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 3 Name</Name>
    <Val/>
  </String>
</Cluster>
"""
initial_dae_settings = r"""<?xml version="1.0"?>
<Cluster>
  <Name>Data Acquisition</Name>
  <NumElts>23</NumElts>
  <I32>
    <Name>Monitor Spectrum</Name>
    <Val>4</Val>
  </I32>
  <DBL>
    <Name>from</Name>
    <Val>1000</Val>
  </DBL>
  <DBL>
    <Name>to</Name>
    <Val>5000</Val>
  </DBL>
  <String>
    <Name>Wiring Table</Name>
    <Val>C:/Instrument/Settings/config/NDXNIMROD/configurations/tables/NIMROD84modules+9monitors+LAB5Oct2012Wiring.dat</Val>
  </String>
  <String>
    <Name>Detector Table</Name>
    <Val>C:/Instrument/Settings/config/NDXNIMROD/configurations/tables/NIMROD84modules+9monitors+LAB5Oct2012Detector.dat</Val>
  </String>
  <String>
    <Name>Spectra Table</Name>
    <Val>C:/Instrument/Settings/config/NDXNIMROD/configurations/tables/NIMROD84modules+9monitors+LAB5Oct2012Spectra.dat</Val>
  </String>
  <EW>
    <Name>DAETimingSource</Name>
    <Choice>ISIS</Choice>
    <Choice>Internal Test Clock</Choice>
    <Choice>SMP</Choice>
    <Choice>Muon Cerenkov</Choice>
    <Choice>Muon MS</Choice>
    <Choice>ISIS (first TS1)</Choice>
    <Choice>TS1 Only</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>SMP (Chopper) Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Veto 0</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Muon MS Mode</Name>
    <Choice>DISABLED</Choice>
    <Choice>ENABLED</Choice>
    <Val>1</Val>
  </EW>
  <EW>
    <Name> Fermi Chopper Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <DBL>
    <Name>FC Delay</Name>
    <Val>0</Val>
  </DBL>
  <DBL>
    <Name>FC Width</Name>
    <Val>0</Val>
  </DBL>
  <EW>
    <Name>Veto 1</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Veto 2</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Veto 3</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Muon Cerenkov Pulse</Name>
    <Choice>FIRST</Choice>
    <Choice>SECOND</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name> TS2 Pulse Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name> ISIS 50Hz Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <String>
    <Name>Veto 0 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 1 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 2 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 3 Name</Name>
    <Val/>
  </String>
</Cluster>
"""
