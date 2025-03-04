//
// jtag.v
//
// JTAG stub model
//
// Original Author: JOhn Fredine
// Original Date: Feb. 20, 2025
//
// Copyright 2025 Natcast
//

`default_nettype none

`define JTAG_RESET      4'h0
`define JTAG_IDLE       4'h1
`define JTAG_SELECT_DR  4'h2
`define JTAG_CAPTURE_DR 4'h3
`define JTAG_SHIFT_DR   4'h4
`define JTAG_EXIT1_DR   4'h5
`define JTAG_PAUSE_DR   4'h6
`define JTAG_EXIT2_DR   4'h7
`define JTAG_UPDATE_DR  4'h8
`define JTAG_SELECT_IR  4'h9
`define JTAG_CAPTURE_IR 4'ha
`define JTAG_SHIFT_IR   4'hb
`define JTAG_EXIT1_IR   4'hc
`define JTAG_PAUSE_IR   4'hd
`define JTAG_EXIT2_IR   4'he
`define JTAG_UPDATE_IR  4'hf

`define JTAG_NOP        2'h0
`define JTAG_SCRATCH_8  2'h1
`define JTAG_SCRATCH_16 2'h2
`define JTAG_SCRATCH_32 2'h3

module jtag (
    input  wire trst,
    input  wire tck,
    input  wire tms,
    input  wire tdi,
    output wire tdo
);
    reg  [ 3:0] jtag_state;
    reg  [ 3:0] next_jtag_state;
    reg  [ 1:0] ir;

    reg  [31:0] scratch;
    reg  [ 7:0] scratch_8;
    reg  [15:0] scratch_16;
    reg  [31:0] scratch_32;
    reg         tdo_int;

    // JTAG state machine
    always @(*) begin
        if (trst) begin
            next_jtag_state = `JTAG_RESET;
        end
        else begin
            case (jtag_state)
                `JTAG_RESET:      next_jtag_state = tms ? `JTAG_RESET
                                                        : `JTAG_IDLE;
                `JTAG_IDLE:       next_jtag_state = tms ? `JTAG_SELECT_DR
                                                        : `JTAG_IDLE;
                `JTAG_SELECT_DR:  next_jtag_state = tms ? `JTAG_SELECT_IR
                                                        : `JTAG_CAPTURE_DR;
                `JTAG_CAPTURE_DR: next_jtag_state = tms ? `JTAG_EXIT1_DR
                                                        : `JTAG_SHIFT_DR;
                `JTAG_SHIFT_DR:   next_jtag_state = tms ? `JTAG_EXIT1_DR
                                                        : `JTAG_SHIFT_DR;
                `JTAG_EXIT1_DR:   next_jtag_state = tms ? `JTAG_UPDATE_DR
                                                        : `JTAG_PAUSE_DR;
                `JTAG_PAUSE_DR:   next_jtag_state = tms ? `JTAG_EXIT2_DR
                                                        : `JTAG_PAUSE_DR;
                `JTAG_EXIT2_DR:   next_jtag_state = tms ? `JTAG_UPDATE_DR
                                                        : `JTAG_SHIFT_DR;
                `JTAG_UPDATE_DR:  next_jtag_state = tms ? `JTAG_SELECT_DR
                                                        : `JTAG_IDLE;
                `JTAG_SELECT_IR:  next_jtag_state = tms ? `JTAG_RESET
                                                        : `JTAG_CAPTURE_IR;
                `JTAG_CAPTURE_IR: next_jtag_state = tms ? `JTAG_EXIT1_IR
                                                        : `JTAG_SHIFT_IR;
                `JTAG_SHIFT_IR:   next_jtag_state = tms ? `JTAG_EXIT1_IR
                                                        : `JTAG_SHIFT_IR;
                `JTAG_EXIT1_IR:   next_jtag_state = tms ? `JTAG_UPDATE_IR
                                                        : `JTAG_PAUSE_IR;
                `JTAG_PAUSE_IR:   next_jtag_state = tms ? `JTAG_EXIT2_IR
                                                        : `JTAG_PAUSE_IR;
                `JTAG_EXIT2_IR:   next_jtag_state = tms ? `JTAG_UPDATE_IR
                                                        : `JTAG_SHIFT_IR;
                `JTAG_UPDATE_IR:  next_jtag_state = tms ? `JTAG_SELECT_DR
                                                        : `JTAG_IDLE;
            endcase
        end
    end

    always @(posedge tck) begin
        jtag_state <= next_jtag_state;
    end


    // shift IR
    always @(posedge tck) begin
        if (jtag_state == `JTAG_CAPTURE_IR) begin
            ir <= `JTAG_NOP;
        end else if (jtag_state == `JTAG_SHIFT_IR) begin
            ir <= {tdi, ir[1]};
        end
    end

    // shift DR
    always @(posedge tck) begin
        if (jtag_state == `JTAG_CAPTURE_DR) begin
            case (ir)
                `JTAG_SCRATCH_8:  scratch <= {24'h0, scratch_8};
                `JTAG_SCRATCH_16: scratch <= {16'h0, scratch_16};
                default:          scratch <= scratch_32;
            endcase
        end else if (jtag_state == `JTAG_SHIFT_DR) begin
            case (ir)
                `JTAG_SCRATCH_8:  scratch <= {24'h0, tdi, scratch[7:1]};
                `JTAG_SCRATCH_16: scratch <= {16'h0, tdi, scratch[15:1]};
                default:          scratch <= {tdi, scratch[31:1]};
            endcase
        end else if (jtag_state == `JTAG_UPDATE_DR) begin
            case (ir)
                `JTAG_SCRATCH_8:  scratch_8  <= scratch[7:0];
                `JTAG_SCRATCH_16: scratch_16 <= scratch[15:0];
                default:          scratch_32 <= scratch;
            endcase
        end
    end

    // shift out
    // the shift out (done on negedge) lags the shift in (done on posedge)
    // so we still need to do the final shift out if the state is EXIT1
    always @(negedge tck) begin
        if ((jtag_state == `JTAG_SHIFT_IR)
            || (jtag_state == `JTAG_EXIT1_IR)) begin
            tdo_int <= ir[0];
        end else if ((jtag_state == `JTAG_SHIFT_DR)
                     || (jtag_state == `JTAG_EXIT1_IR)) begin
            tdo_int <= scratch[0];
        end
    end

    assign tdo = tdo_int;

endmodule
