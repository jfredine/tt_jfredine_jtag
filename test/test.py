import os
import logging
import cocotb
import cocotb.clock

async def jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern):

    # determine longest pattern and extend others to that length
    trst_len = len(trst_pattern)
    tms_len = len(tms_pattern)
    tdi_len = len(tdi_pattern)

    max_len = max(trst_len, tms_len, tdi_len)
    if (trst_len < max_len):
        trst_pattern = trst_pattern + (trst_pattern[-1],) * (max_len - trst_len)
    if (tms_len < max_len):
        tms_pattern = tms_pattern + (tms_pattern[-1],) * (max_len - tms_len)
    if (tdi_len < max_len):
        tdi_pattern = tdi_pattern + (tdi_pattern[-1],) * (max_len - tdi_len)

    tdo_patterns = ()
    curr_tdo_pattern = ()

    # synchronize to falling edge clock state
    if dut.clk.value == 1:
        await cocotb.triggers.FallingEdge(dut.clk)
    curr_state = dut.jtag_state.value
    prev_state = curr_state

    for (trst, tms, tdi) in zip(trst_pattern, tms_pattern, tdi_pattern):
        # inject new inputs at falling edge of clock
        dut.trst.value = trst
        dut.tms.value = tms
        dut.tdi.value = tdi
        dut._log.debug("(trst, tms, tdi) = (%s, %s, %s)", trst, tms, tdi)

        # wait for rising edge to possibly sample tdo
        await cocotb.triggers.RisingEdge(dut.clk)

        dut._log.debug("-- After rising Edge --")
        dut._log.debug("prev_state = %s, curr_state = %s",
                       prev_state, curr_state)

        # sample output if in shift state
        if (curr_state == 4) and (prev_state != 4):
            curr_tdo_pattern = ()
        elif (prev_state == 4):
            dut._log.debug("tdo = %s", dut.tdo.value)
            curr_tdo_pattern = curr_tdo_pattern + (dut.tdo.value,)
            dut._log.debug("curr_tdo_pattern = %s", curr_tdo_pattern)
            if dut.jtag_state.value != 4:
                dut._log.debug("adding tdo_pattern = %s", curr_tdo_pattern)
                tdo_patterns = tdo_patterns + (curr_tdo_pattern,)

        # wait for falling edge to drive new inputs
        await cocotb.triggers.FallingEdge(dut.clk)
        prev_state = curr_state
        curr_state = dut.jtag_state.value
        dut._log.debug("-- After falling Edge --")
        dut._log.debug("prev_state = %s, curr_state = %s",
                       prev_state, curr_state)

    return tdo_patterns

@cocotb.test()
async def test_scratch_8(dut):
    """Test access to scratch_8 register"""

    # set logging
    if 'JTAG_LOGGING' in os.environ:
        level = os.environ['JTAG_LOGGING'].upper()
        try:
            dut._log.setLevel(getattr(logging, level))
        except AttributeError:
            print("Unknown logging level {level} ignored")

    clock = cocotb.clock.Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # reset JTAG to known state
    dut._log.debug("Reset JTAG")
    trst_pattern =(1, 1, 1, 1, 0)
    tms_pattern  =(0, 0, 0, 0, 0)  # end in idle state
    tdi_pattern  =(0, )            # unused
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift in scratch_8 instruction
    dut._log.debug("Set IR to scratch_8")
    trst_pattern =(0, )
    tms_pattern  =(1, 1, 0, 0,              # Advance to shift IR
                   0, 0, 0, 0, 0, 1,        # shift IR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0, 0,              # filler until shift IR
                   1, 0, 0, 0, 0, 0,        # shift 01 (scratch_8) into IR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift value into scratch_8 register
    dut._log.debug("Shift in 0xab to scratch_8 register")
    trst_pattern =(0, )
    tms_pattern  =(1, 0, 0,                 # Advance to shift DR
                   0, 0, 0, 0, 0, 0, 0, 1,  # shift DR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0,                 # filler until shift IR
                   1, 1, 0, 1, 0, 1, 0, 1,  # shift ab into DR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # readback value from scratch_8 register
    dut._log.debug("Shift out value of scratch_8 register")
    trst_pattern = (0,)
    tms_pattern  = (1, 0, 0,                 # Advance from idle to shift DR
                    0, 0, 0, 0, 0, 0, 0, 1,  # Shift DR and move to exit 1
                    1, 0)                    # Return to idle
    tdi_pattern  = (0,)
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    tdo_capture = 0;
    for i in reversed(tdo_patterns[0]):
        tdo_capture = (tdo_capture << 1) | i

    assert tdo_capture == 0xab, "DR is not 0xab!"


@cocotb.test()
async def test_scratch_16(dut):
    """Test access to scratch_16 register"""

    clock = cocotb.clock.Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # reset JTAG to known state
    dut._log.debug("Reset JTAG")
    trst_pattern =(1, 1, 1, 1, 0)
    tms_pattern  =(0, 0, 0, 0, 0)  # end in idle state
    tdi_pattern  =(0, )            # unused
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift in scratch_16 instruction
    dut._log.debug("Set IR to scratch_16")
    trst_pattern =(0, )
    tms_pattern  =(1, 1, 0, 0,              # Advance to shift IR
                   0, 0, 0, 0, 0, 1,        # shift IR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0, 0,              # filler until shift IR
                   0, 1, 0, 0, 0, 0,        # shift 02 (scratch_16) into IR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift value into scratch_16 register
    dut._log.debug("Shift in 0xaced to scratch_16 register")
    trst_pattern =(0, )
    tms_pattern  =(1, 0, 0,                 # Advance to shift DR
                   0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 1,  # shift DR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0,                 # filler until shift IR
                   1, 0, 1, 1, 0, 1, 1, 1,
                   0, 0, 1, 1, 0, 1, 0, 1,  # shift aced into DR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # readback value from scratch_16 register
    dut._log.debug("Shift out value of scratch_16 register")
    trst_pattern = (0,)
    tms_pattern  = (1, 0, 0,                 # Advance from idle to shift DR
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 1,  # Shift DR and move to exit 1
                    1, 0)                    # Return to idle
    tdi_pattern  = (0,)
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    tdo_capture = 0;
    for i in reversed(tdo_patterns[0]):
        tdo_capture = (tdo_capture << 1) | i

    assert tdo_capture == 0xaced, "DR is not 0xaced!"


@cocotb.test()
async def test_scratch_32(dut):
    """Test access to scratch_32 register"""

    clock = cocotb.clock.Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # reset JTAG to known state
    dut._log.debug("Reset JTAG")
    trst_pattern =(1, 1, 1, 1, 0)
    tms_pattern  =(0, 0, 0, 0, 0)  # end in idle state
    tdi_pattern  =(0, )            # unused
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift in scratch_32 instruction
    dut._log.debug("Set IR to scratch_32")
    trst_pattern =(0, )
    tms_pattern  =(1, 1, 0, 0,              # Advance to shift IR
                   0, 0, 0, 0, 0, 1,        # shift IR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0, 0,              # filler until shift IR
                   1, 1, 0, 0, 0, 0,        # shift 03 (scratch_32) into IR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift value into scratch_32 register
    dut._log.debug("Shift in 0xaced to scratch_32 register")
    trst_pattern =(0, )
    tms_pattern  =(1, 0, 0,                 # Advance to shift DR
                   0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 1,  # shift DR and move to exit 1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0,                 # filler until shift IR
                   0, 1, 1, 1, 1, 1, 1, 1,
                   0, 1, 0, 1, 0, 0, 1, 1,
                   1, 0, 1, 1, 0, 1, 1, 1,
                   0, 0, 1, 1, 0, 1, 0, 1,  # shift aced into DR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # readback value from scratch_32 register
    dut._log.debug("Shift out value of scratch_32 register")
    trst_pattern = (0,)
    tms_pattern  = (1, 0, 0,                 # Advance from idle to shift DR
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 1,  # Shift DR and move to exit 1
                    1, 0)                    # Return to idle
    tdi_pattern  = (0,)
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    tdo_capture = 0;
    for i in reversed(tdo_patterns[0]):
        tdo_capture = (tdo_capture << 1) | i

    assert tdo_capture == 0xacedcafe, "DR is not 0xacedcafe!"


@cocotb.test()
async def test_idcode_after_reset(dut):
    """Test access to idcode register after reset"""

    clock = cocotb.clock.Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # reset JTAG to known state
    dut._log.debug("Reset JTAG")
    trst_pattern =(1, 1, 1, 1, 0)
    tms_pattern  =(0, 0, 0, 0, 0)  # end in idle state
    tdi_pattern  =(0, )            # unused
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # readback value from idcode register
    dut._log.debug("Shift out value of idcode register")
    trst_pattern = (0,)
    tms_pattern  = (1, 0, 0,                 # Advance from idle to shift DR
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 1,  # Shift DR and move to exit 1
                    1, 0)                    # Return to idle
    tdi_pattern  = (0,)
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    tdo_capture = 0;
    for i in reversed(tdo_patterns[0]):
        tdo_capture = (tdo_capture << 1) | i

    assert tdo_capture == 0xbeefcafe, "DR is not 0xbeefcafe!"


@cocotb.test()
async def test_idcode_from_instruction(dut):
    """Test access to idcode register from instruction"""

    clock = cocotb.clock.Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # reset JTAG to known state
    dut._log.debug("Reset JTAG")
    trst_pattern =(1, 1, 1, 1, 0)
    tms_pattern  =(0, 0, 0, 0, 0)  # end in idle state
    tdi_pattern  =(0, )            # unused
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift in scratch_8 instruction
    dut._log.debug("Set IR to scratch_8")
    trst_pattern =(0, )
    tms_pattern  =(1, 1, 0, 0,              # Advance to shift IR
                   0, 0, 0, 0, 0, 1,        # shift IR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0, 0,              # filler until shift IR
                   1, 0, 0, 0, 0, 0,        # shift 01 (scratch_8) into IR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift value into scratch_8 register
    dut._log.debug("Shift in 0xab to scratch_8 register")
    trst_pattern =(0, )
    tms_pattern  =(1, 0, 0,                 # Advance to shift DR
                   0, 0, 0, 0, 0, 0, 0, 1,  # shift DR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0,                 # filler until shift IR
                   1, 1, 0, 1, 0, 1, 0, 1,  # shift ab into DR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift in idcode instruction
    dut._log.debug("Set IR to idcode")
    trst_pattern =(0, )
    tms_pattern  =(1, 1, 0, 0,              # Advance to shift IR
                   0, 0, 0, 0, 0, 1,        # shift IR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0, 0,              # filler until shift IR
                   0, 1, 1, 1, 1, 1,        # shift 3e (idcode) into IR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # readback value from idcode register
    dut._log.debug("Shift out value of idcode register")
    trst_pattern = (0,)
    tms_pattern  = (1, 0, 0,                 # Advance from idle to shift DR
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 1,  # Shift DR and move to exit 1
                    1, 0)                    # Return to idle
    tdi_pattern  = (0,)
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    tdo_capture = 0;
    for i in reversed(tdo_patterns[0]):
        tdo_capture = (tdo_capture << 1) | i

    assert tdo_capture == 0xbeefcafe, "DR is not 0xbeefcafe!"


@cocotb.test()
async def test_bypass(dut):
    """Test bypass instruction"""

    clock = cocotb.clock.Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # reset JTAG to known state
    dut._log.debug("Reset JTAG")
    trst_pattern =(1, 1, 1, 1, 0)
    tms_pattern  =(0, 0, 0, 0, 0)  # end in idle state
    tdi_pattern  =(0, )            # unused
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift in bypass instruction
    dut._log.debug("Set IR to bypass")
    trst_pattern =(0, )
    tms_pattern  =(1, 1, 0, 0,              # Advance to shift IR
                   0, 0, 0, 0, 0, 1,        # shift IR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0, 0,              # filler until shift IR
                   1, 1, 1, 1, 1, 1,        # shift 3f (bypass) into IR
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # shift value through the bypass register
    dut._log.debug("Shift a pattern through the bypass register")
    trst_pattern =(0, )
    tms_pattern  =(1, 0, 0,                 # Advance to shift DR
                   0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 1,  # shift DR and move to exit1
                   1, 0)                    # advance to idle

    tdi_pattern  =(0, 0, 0,                 # filler until shift IR
                   1, 0, 1, 1, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 1, 1, 0, 0,  # value through bypass
                   0)                       # filler
    tdo_patterns = await jtag_xaction(dut, trst_pattern, tms_pattern, tdi_pattern)

    # in this case we drop the last bit because we needed one extra clock
    # to pass the data through the single bit register in the chain
    tdo_capture = 0;
    for i in reversed(tdo_patterns[0][1:]):
        tdo_capture = (tdo_capture << 1) | i

    assert tdo_capture == 0x600D, "DR is not 0x600D!"
