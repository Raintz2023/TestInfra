USE chip
VOLTAGE = VS0

BEGIN
    <0> START
        NOP *
        NOP | DATA = 1 : RDQSH ; R < DATA ; CPA *
    STOP
END
