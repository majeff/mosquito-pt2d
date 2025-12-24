/****************************************************************************
	*	@笔者	：	W
	*	@日期	：	2019年12月28日
	*	@所属	：	杭州众灵科技
	*	@论坛	：	www.ZL-robot.com
	*	@功能	：	ZL-KPZ控制板（AR版）模块例程4————串口的基本用法
	*	@函数列表：
	*	1.	void setup(void) -- 初始化函数
	*	2.	void loop(void) -- 主循环函数
 ****************************************************************************/

/*******全局变量宏定义*******/
#define UART_RECEIVE_BUF_SIZE 100

/*******全局变量定义*******/
u8 i=0;
u8 uart_receive_buf[UART_RECEIVE_BUF_SIZE]={0}, uart_receive_buf_index, uart_get_ok;

void setup(void) {																																																																																																																															//ZL
	setup_led();			//初始化LED信号灯
	setup_beep();			//初始化蜂鸣器BEEP
	setup_uart();			//初始化串口
	setup_finish();			//初始化完成
}
void loop(void) {
	loop_uart();			//循环接收串口数据并处理
}
