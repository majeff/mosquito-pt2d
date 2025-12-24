/****************************************************************************
	*	@笔者	：	W
	*	@日期	：	2019年12月28日
	*	@所属	：	杭州众灵科技
	*	@论坛	：	www.ZL-robot.com
	*	@功能	：	存放蜂鸣器BEEP相关的函数
	*	@函数列表：
	*	1.	void beep_init(void) -- 初始化蜂鸣器BEEP
	*	2.	void BEEP_F(void) -- 翻转蜂鸣器BEEP
 ****************************************************************************/

/*******BEEP管脚映射表*******/
#define BEEP_PIN			4

/*******BEEP快捷指令表*******/
#define BEEP	 digitalRead(BEEP_PIN)			//读取蜂鸣器BEEP状态
#define BEEP_H() digitalWrite(BEEP_PIN,LOW)		//蜂鸣器BEEP打开
#define BEEP_L() digitalWrite(BEEP_PIN,HIGH)	//蜂鸣器BEEP关闭

/***********************************************
	函数名称:		beep_init(void)
	功能介绍:		初始化蜂鸣器
	函数参数:		无
	返回值:			无
 ***********************************************/
void beep_init(void) {
	pinMode(BEEP_PIN,OUTPUT);					//设置引脚为输出模式
}

/***********************************************
	函数名称:		BEEP_F(void)
	功能介绍:		翻转蜂鸣器BEEP
	函数参数:		无
	返回值:			无
 ***********************************************/
void BEEP_F(void) {
	if(BEEP==0)	
		BEEP_L();
	else 
		BEEP_H();
}
