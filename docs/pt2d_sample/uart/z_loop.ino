/****************************************************************************
	*	@笔者	：	W
	*	@日期	：	2019年12月28日
	*	@所属	：	杭州众灵科技
	*	@论坛	：	www.ZL-robot.com
	*	@功能	：	存放永久循环执行的函数
	*	@函数列表：
	*	1.	void loop_uart(void) -- 循环接收处理串口数据
 ****************************************************************************/

/***********************************************
	函数名称:		loop_uart() 
	功能介绍:		循环接收处理串口数据
	函数参数:		无
	返回值:			无
 ***********************************************/
void loop_uart(void) {
	if(uart_get_ok) {
		if((uart_receive_buf[1]=='L') && (uart_receive_buf[2]=='E') && (uart_receive_buf[3]=='D') && (uart_receive_buf[4]=='O') && (uart_receive_buf[5]=='N')) {
			LED_H();
		}
		else if((uart_receive_buf[1]=='L') && (uart_receive_buf[2]=='E') && (uart_receive_buf[3]=='D') && (uart_receive_buf[4]=='O') && (uart_receive_buf[5]=='F') && (uart_receive_buf[6]=='F')) {
			LED_L();
		}
		else if((uart_receive_buf[1]=='B') && (uart_receive_buf[2]=='E') && (uart_receive_buf[3]=='E') && (uart_receive_buf[4]=='P') && (uart_receive_buf[5]=='O') && (uart_receive_buf[6]=='N')) {
			BEEP_H();
		}
		else if((uart_receive_buf[1]=='B') && (uart_receive_buf[2]=='E') && (uart_receive_buf[3]=='E') && (uart_receive_buf[4]=='P') && (uart_receive_buf[5]=='O') && (uart_receive_buf[6]=='F') && (uart_receive_buf[7]=='F')) {
			BEEP_L();
		}
		uart_receive_buf_index = 0;
		uart_get_ok = 0;
		memset(uart_receive_buf, 0, sizeof(uart_receive_buf));
	}
}
