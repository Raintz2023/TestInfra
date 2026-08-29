# TestInfra Verilog 与 C++ 底层说明

本文说明 Python pattern runtime 以下的 pin-level 仿真后端。ATE 调度和
DUT 内部逻辑仍然使用数字模型，可选电压层只模拟芯片接口处有限的转换速度。

## 整体结构

```text
Python runtime
    -> C++ ATE phase 调度器
    -> Socket
       -> PinIn 数字事件驱动
       -> ATE 理想 VIL/VIH 驱动电压
       -> DUT 自己拥有的输入电气模型
       -> DUT 数字核心
       -> DUT 自己拥有的输出电气模型
       -> ATE VOL/VOH 比较器
       -> PinOut 采样器
    -> sample record 与 compare result
```

`ATE::advance_phase()` 是最小时间单位。它先分派到期的 drive、sample 和
alert event，再依次求值 `ATE_CLK=0` 与上升沿。一个 timing period 包含
`TimingSet.prd` 个 phase。

## 原数字后端

`PinInDriver` 负责硬件 drive delay 和 duration，到期后给出数字目标值。每个
延迟事件同时携带 active 值和该 pin 配置的默认返回值；duration 结束时回到
`DEF`，而不是固定回到 0。这对 idle level 为 1 的 DQ/DQS 尤其重要。
`PinOutSampler` 负责硬件 sample delay，同时锁存数字采样值与电压有效位。

某个 pin 未开启电压仿真时，电压接口采用组合旁路，原有数字 pattern 的
phase 行为不发生变化。

对于 `Chip` DUT，干净的 RTL 模块只保留真实数字输入/输出 pin。如果存在
`ChipAnalogWrapper`，generated `DUT.v` 会实例化这个 shell；ATE 电压、
POWER、slew、skew 等基础设施都接入 wrapper，再由 wrapper 连接到底层
`Dram`。pin 编号和后续 `soc.pat` 自动生成仍然以干净的 `Chip.v` header
作为唯一来源。

## 输入电压链路

```text
ATE 数字目标 -> 理想 VIL/VIH -> DUT input slew -> DUT VREF 比较器 -> DUT
```

- ATE 驱动 0 选择 `vil_uv`，驱动 1 选择 `vih_uv`。
- `AteInputDriver` 是理想组合电压源，数字 0/1 会立即把 `ATE_PIN_IN_UV`
  切换到 VIL/VIH，不产生衰减。
- `DutInputComparator` 由需要它的 DUT 层级实例化。当前 `Chip -> Dram`
  路径中，`Dram.v` 自己拥有 DQ/DQS 的输入 slew 和 Vref；
  `PIN_IN_UV` 从下一个 ATE phase 开始变化。
- pad 电压大于等于 DUT 自己的 Vref 时，DUT core 看到 1，否则看到 0。

ATE 默认 VIL=0 uV、VIH=1,200,000 uV。对于 `Dram`，Vref 由 `VDDQ` 电源轨和
`MR5` 决定：code 0 到 200 对应 0% 到 100% VDDQ，大于 200 的 code 按
100% 处理。复位默认 code 为 200。

## 输出电压链路

```text
DUT 数字输出 -> DUT_LOW/DUT_HIGH -> 线性斜坡 -> ATE VOL/VOH 比较器
```

- `DutOutputDriver` 由需要它的 DUT 层级实例化。当前 `Chip -> Dram`
  路径中，`Dram.v` 自己拥有 DQ/DQS 的 LOW/HIGH 输出电压和输出 slew。
- `AteOutputComparator` 只负责 VOL/VOH 判定。
- 电压小于等于 `vol_uv` 时，ATE 得到有效的 0。
- 电压大于等于 `voh_uv` 时，ATE 得到有效的 1。
- VOL 与 VOH 之间属于无效区。

无效采样仍然产生 `SAMP_ALERT`。C++ 将有效性保存到
`SampleRecord.valid_mask`；请求比较的任意 pin 无效时 compare 直接 fail，
不会丢弃采样或无限等待。

默认值为 DUT_LOW=0 uV、DUT_HIGH=1,200,000 uV、VOL=300,000 uV、
VOH=900,000 uV，上升和下降速度均为 100,000 uV/phase。

## C++ Testbench 接口

`ATE` 是负责 phase 调度、Socket 总线和 sample record 的底层引擎。新的独立
C++ 调试程序推荐使用 `AteBench`：它只增加具名 pin 和原子 vector row，不
引入 parser、DSL 或 codegen。

首先集中声明 timing、pin、waveform、default 和可选电压配置：

```cpp
AteBenchConfig config{
    .wave_path = "C++/wave/wave_voltage.vcd",
    .trace_enable = true,
    .timing = timing,
    .inputs = {
        {"CLK",  0, 1, DriveWaveform::rzz(), 0},
        {"ADDR", 4, 8, DriveWaveform::nrz(), 0, ate_input_voltage},
        {"MRR", 23, 1, DriveWaveform::rz(), 0},
    },
    .outputs = {
        {"DQ_TX_BIT", 1, 1, ate_output_voltage},
    },
    .dut_interface = {
        .inputs = {{"ADDR", dut_input_interface}},
        .outputs = {{"DQ_TX_BIT", dut_output_interface}},
    },
};
```

测试主体只描述 vector row：

```cpp
AteBench bench(std::move(config));
bench.run(VectorRow{}.drive("ADDR", 3).pulse("MRR"));
bench.wait("DQ_OE");
bench.run(VectorRow{}.sample("DQ_TX_BIT", 1));
```

同一个 `VectorRow` 的 action 使用相同 row-start phase。`pulse()` 只接受单 bit
RZ input，并自动调度两个 RZ edge；`drive()` 只接受 input，`sample()` 只接受
output；同一行重复覆盖相同 pin 会报错。特殊实验仍可通过 `engine()` 访问底层。

`wait(output_name, max_rows)` 会记录 output field 的当前值，并不断执行空 vector
row，直到该值发生变化。它读取连续的 ATE comparator monitor，不会创建 sample
或 compare record。`max_rows=0`（默认值）表示不限制等待行数；传入非零上限时，
超时会抛出异常。input pin 名称会被拒绝。

对于功能式事件驱动 bench，`AteEvent` 可以封装可复用的 row 序列：

```cpp
AteEvent write_frame{"write_frame"};
write_frame
    .run(VectorRow{}.drive("DQS_RX_BIT", 0))
    .run(VectorRow{}.drive("DQS_RX_BIT", 1));

bench.wait_rising("DQ_IE", 100, write_frame);

// 不需要 monitor 触发时，也可以显式运行同一个 event。
bench.run(write_frame);
```

`wait(output, max_rows, event)`、`wait_rising(...)` 和 `wait_falling(...)`
会继续推进空 vector row，直到指定变化发生，然后同步执行 event 并返回
`WaitResult`。handler 在触发变化的等待 row 完成后执行，执行完再回到原来的
测试顺序。`bench.run(event)` 则是在没有 monitor 触发需求时显式执行同一段
封装。第一版有意禁止嵌套 event-handler wait，避免调试流变成隐式递归。

DRAM 将 `DQ_IE` 定义为事件驱动的写接收 ready 锚点。WL 到期后，`DQ_IE`
保持为高并等待 14-cycle DQS/DQ frame，最长等待 64 cycles。因此 C++ 功能
测试可以先等待 `DQ_IE` 再发送 frame；Python 精确时序测试仍可提前调度同一
段 frame。

## C++ 电压配置接口

ATE 与 DUT 的电气参数使用不同类型明确所有权：

```text
AteInputVoltageConfig    VIL、VIH
AteOutputVoltageConfig   VOL、VOH
DutInputInterfaceConfig  DUT-owned pad 的输入 slew 覆盖
DutOutputInterfaceConfig DUT-owned pad 的 LOW/HIGH 与输出 slew 覆盖
DutSkewConfig            DQ/DQS skew 覆盖，用于 C++ 底层验证
POWER VDDQ                DUT 电源轨，当前由 C++ bench 设置
```

DUT interface 类型是被测 DUT 的验证覆盖口，不是普通 ATE pin。
`AteBenchConfig` 将其放在独立的 `dut_interface`，不与 `inputs/outputs`
混写：

```cpp
config.inputs = {{"ADDR", 4, 8, DriveWaveform::nrz(), 0, ate_input_voltage}};
config.outputs = {{"DQ_TX_BIT", 1, 1, ate_output_voltage}};
config.dut_interface.inputs = {{"ADDR", dut_input_interface}};
config.dut_interface.outputs = {{"DQ_TX_BIT", dut_output_interface}};
```

`AteBenchConfig.power_uv["VDDQ"]` 在 C++ 中设置当前 DUT 电源轨。`Dram`
使用这个电源轨和 `MR5` 计算 DQ/DQS 输入 Vref。C++ bench 中也可以通过
`set_power_uv("VDDQ", uv)` 修改。Python schema 使用 `soc.pat` 中的
`POWER VDDQ { SUP: VDC }` 和 `vol.pat` 的 `VSx` 中唯一的顶层
`VDC: ...`，再通过 `session.ti_voltage("VS1").vdc` 接到同一条底层路径。根 pattern 必须在
`BEGIN` 前用 `VOLTAGE = VS1` 固定选择一个电压组。scheduler 构造时只应用
一次电压，vector row 之间不能切换。

`VS0 { @digital }` 选择直接数字路径，在整个运行期间关闭 DUT DQ/DQS 电气
接口和 ATE VOL/VOH 比较器；模拟 VS 会启用两者。Timing BASE 和 command
delay 只移动数字 pin 事件，VIL/VIH 与 VDC 不再进入延迟事件队列。VIL、VIH、
VOL、VOH 既可写绝对电压，也可写成 VDC 的无单位比例，但都不能超过 VDC；
Python 修改后的配置会在每次运行前再次校验。

`current_ate_input_voltage_uv()` 查询 ATE 理想驱动电压，
`current_input_voltage_uv()` 查询 DUT pad 实际接收电压。ATE 输入电压只要求
`VIL < VIH`；DUT Vref 由 DUT 自己决定，不再和 ATE 配置做交叉限制。
ATE 输出判定阈值只要求 `VOL <= VOH`，DUT 输出模型只要求
`DUT_LOW < DUT_HIGH`。VOL/VOH 允许扫到 DUT 输出范围之外，用来寻找真实
compare 窗口；范围外的阈值会自然表现为 invalid sample 或 compare fail。
slew step 不能为零。

DUT 电气误差覆盖口仍然只暴露给 C++。Python pattern/runtime 现在可以从
`vol.pat` 配置 ATE 侧 VIN/VOUT 阈值和 POWER rail，同时继续观察 RTL 自己
决定的 slew、low/high、Vref 与 skew 行为。

## Surfer 查看电压

trace 构建会输出 ATE 理想电压 `ATE_PIN_IN_UV`、DUT pad 电压 `PIN_IN_UV`
与输出电压 `PIN_OUT_UV`，每个 pin 占 32 bit，单位 uV。
pin `n` 对应切片 `[32*n+31:32*n]`。在 Surfer 中将该切片设置为 unsigned
numeric 或 analog rendering，即可观察阶梯式电压曲线。

模拟渲染要求 Surfer 0.6 或更新版本。OSS CAD Suite 自带的版本可能是没有
analog renderer 的 0.4 开发版；当前机器应明确运行 Homebrew 版本：

```text
/opt/homebrew/bin/surfer C++/wave/wave_voltage.vcd
```

演示波形中可以对比 ATE 理想输入电压和 DUT-owned pad 电压。当前
`Chip -> Dram` 路径中，DQ/DQS 输入 pad 电压在 `Dram` 内部的 input
comparator 实例里，输出 pad 电压在 `Dram` 内部的 output driver 实例里。
wrapper 级别的 `PIN_IN_UV` 和 `PIN_OUT_UV` 总线也会把同一组 per-pin uV
值送回 Socket。然后在信号右键菜单选择 `Analog`，渲染方式选择 `Step`
或 `Interpolated`。

构建模式必须成对使用：

```text
fish -c 'source Config/config.fish; vbuild && cbuild'
fish -c 'source Config/config.fish; vbuild --fast && cbuild --fast'
```

trace 模式用于 VCD；fast 模式不生成波形，创建 ATE 时应使用
`trace_enable=false`。

fish 中的 `cwave/pwave` 会明确调用 Homebrew Surfer，因此可以直接使用
`cwave voltage` 打开演示，不会再被 OSS CAD Suite 的旧版 Surfer 抢先。
