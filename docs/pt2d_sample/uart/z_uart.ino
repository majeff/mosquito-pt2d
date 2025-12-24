/****************************************************************************
	*	@笔者	：	W
	*	@日期	：	2019年12月28日
	*	@所属	：	杭州众灵科技
	*	@论坛	：	www.ZL-robot.com
	*	@功能	：	存放串口相关的函数
	*	@函数列表：
	*	1.	void uart_init(u32 baud) -- 初始化串口
	*	2.	void uart_send_byte(u8 dat) -- 串口发送字节
	*	3.	void uart_send_str(char *s) -- 串口发送字符串
	*	4.	void serialEvent -- 串口中断函数
 ****************************************************************************/

/***********************************************
	函数名称:		uart_init() 
	功能介绍:		初始化串口
	函数参数:		baud 波特率
	返回值:			无
 ***********************************************/
void uart_init(u32 baud) {
	Serial.begin(baud);		//初始化波特率为baud
}

/***********************************************
	函数名称:		uart_send_byte() 
	功能介绍:		串口发送字节
	函数参数:		dat 发送的字节
	返回值:			无
 ***********************************************/
void uart_send_byte(u8 dat) {
	Serial.write(dat);
}

/***********************************************
	函数名称:		uart_send_str() 
	功能介绍:		串口发送字符串
	函数参数:		*s 发送的字符串
	返回值:			无
 ***********************************************/
void uart_send_str(char *s) {
	while (*s) {
		Serial.print(*s++);
	}
}

/***********************************************
	函数名称:		serialEvent() 
	功能介绍:		串口中断函数
	函数参数:		无
	返回值:			无
 ***********************************************/
void serialEvent(void) {
	static u8 sbuf_bak;

	while(Serial.available()) {
		sbuf_bak = Serial.read();
		/*******返回接收到的指令*******/
		uart_send_byte(sbuf_bak);
		/*******若正在执行命令，则不存储命令*******/
		if(uart_get_ok) return;
		/*******检测命令起始*******/
		if(sbuf_bak == '$') {
			uart_receive_buf_index = 0;
		}
		/*******检测命令结尾*******/
		else if(sbuf_bak == '!'){
			uart_receive_buf[uart_receive_buf_index] = sbuf_bak;
			Serial.println();
			uart_get_ok = 1;
			return;
		} 
		uart_receive_buf[uart_receive_buf_index++] = sbuf_bak;
		/*******检测命令长度*******/		
		if(uart_receive_buf_index >= UART_RECEIVE_BUF_SIZE) {
			uart_receive_buf_index = 0;
		}
	}
	return;
}
