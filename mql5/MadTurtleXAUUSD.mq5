#property strict
#property version   "1.00"
#property description "Mad Turtle-style XAUUSD ML EA with strict risk controls"

#include <Trade/Trade.mqh>

CTrade trade;
const double INVALID_ATR = 0.0;

input string InpSymbol = "XAUUSD";
input double InpRiskPct = 0.005; // 0.5%
input double InpDailyLossLimitPct = 0.02;
input double InpMaxDrawdownPct = 0.12;
input int    InpATRPeriod = 14;
input double InpATRStopMult = 1.4;
input bool   InpUseTrailingStop = true;
input double InpTrailingATRMult = 1.2;
input int    InpMaxHoldMinutes = 180;
input int    InpSpreadLimitPoints = 50;
input int    InpMaxSlippagePoints = 20;
input bool   InpEnableNewsFilter = true;
input int    InpNewsBlackoutBeforeMin = 30;
input int    InpNewsBlackoutAfterMin = 30;
input bool   InpEnableSessionFilter = true;
input int    InpLondonStartHourUTC = 7;
input int    InpLondonEndHourUTC = 13;
input int    InpNewYorkStartHourUTC = 13;
input int    InpNewYorkEndHourUTC = 22;
input string InpSignalFile = "signal_pipe.csv";
input string InpLogFile = "mad_turtle_log.csv";
input string InpJsonLogFile = "mad_turtle_log.jsonl";
input long   InpMagic = 4415001;

struct SignalMsg
{
   datetime t;
   string signal;
   double confidence;
   double sl_points;
};

double g_start_day_equity = 0.0;
double g_peak_equity = 0.0;
datetime g_last_signal_ts = 0;
datetime g_position_open_time = 0;
bool g_killed = false;
string g_kill_reason = "";

int OnInit()
{
   if(_Symbol != InpSymbol)
      Print("Warning: attach EA to ", InpSymbol, " chart.");

   g_start_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity = g_start_day_equity;

   int f = FileOpen(InpLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI);
   if(f != INVALID_HANDLE)
   {
      FileWrite(f, "time", "event", "detail", "equity", "balance", "position", "price", "sl", "volume");
      FileClose(f);
   }
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   if(_Symbol != InpSymbol)
      return;

   ResetDayStateIfNeeded();
   UpdateKillSwitch();

   if(g_killed)
   {
      LogEvent("KILL_SWITCH", g_kill_reason);
      return;
   }

   double atr = iATR(InpSymbol, PERIOD_M5, InpATRPeriod, 0);
   if(atr == EMPTY_VALUE || atr <= 0)
      atr = INVALID_ATR;
   ManageOpenPosition(atr);
   if(HasOpenPosition())
      return;

   if(!SessionAllowed())
      return;

   if(!SpreadAllowed())
      return;

   if(InpEnableNewsFilter && IsNewsBlackout())
      return;

   SignalMsg msg;
   if(!ReadSignal(msg))
      return;

   if(msg.t <= g_last_signal_ts)
      return;

   if(msg.signal != "BUY" && msg.signal != "SELL")
      return;

   if(atr <= INVALID_ATR)
      return;

   double stop_points = (msg.sl_points > 0 ? msg.sl_points : atr * InpATRStopMult / _Point);
   double lots = ComputeRiskLot(stop_points);
   if(lots <= 0)
      return;

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxSlippagePoints);

   bool ok = false;
   double price = (msg.signal == "BUY") ? SymbolInfoDouble(InpSymbol, SYMBOL_ASK) : SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   double sl = (msg.signal == "BUY") ? price - stop_points * _Point : price + stop_points * _Point;

   if(msg.signal == "BUY")
      ok = trade.Buy(lots, InpSymbol, 0.0, sl, 0.0, "MadTurtleBUY");
   else
      ok = trade.Sell(lots, InpSymbol, 0.0, sl, 0.0, "MadTurtleSELL");

   if(ok)
   {
      g_last_signal_ts = msg.t;
      g_position_open_time = TimeCurrent();
      LogEvent("ENTRY", msg.signal);
   }
   else
   {
      LogEvent("ENTRY_FAIL", IntegerToString((int)trade.ResultRetcode()));
   }
}

void ManageOpenPosition(double atr)
{
   if(!PositionSelect(InpSymbol))
      return;

   long type = PositionGetInteger(POSITION_TYPE);
   double open = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl = PositionGetDouble(POSITION_SL);
   double current = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(InpSymbol, SYMBOL_BID) : SymbolInfoDouble(InpSymbol, SYMBOL_ASK);

   if(InpUseTrailingStop && atr > INVALID_ATR)
   {
      double trail_dist = InpTrailingATRMult * atr;
      double new_sl = (type == POSITION_TYPE_BUY) ? current - trail_dist : current + trail_dist;
      bool improve = (type == POSITION_TYPE_BUY && new_sl > sl) || (type == POSITION_TYPE_SELL && (sl == 0 || new_sl < sl));
      if(improve)
      {
         trade.PositionModify(InpSymbol, new_sl, 0.0);
      }
   }

   if((TimeCurrent() - g_position_open_time) >= InpMaxHoldMinutes * 60)
   {
      trade.PositionClose(InpSymbol);
      LogEvent("EXIT", "MAX_HOLD");
      return;
   }

   SignalMsg msg;
   if(ReadSignal(msg) && msg.t > g_last_signal_ts)
   {
      if((type == POSITION_TYPE_BUY && msg.signal == "SELL") || (type == POSITION_TYPE_SELL && msg.signal == "BUY"))
      {
         trade.PositionClose(InpSymbol);
         g_last_signal_ts = msg.t;
         LogEvent("EXIT", "COUNTER_SIGNAL");
      }
   }
}

bool HasOpenPosition()
{
   if(!PositionSelect(InpSymbol))
      return false;
   return (PositionGetInteger(POSITION_MAGIC) == InpMagic);
}

void ResetDayStateIfNeeded()
{
   static int last_day = -1;
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   if(last_day != now.day)
   {
      last_day = now.day;
      g_start_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      if(g_start_day_equity > g_peak_equity)
         g_peak_equity = g_start_day_equity;
      g_killed = false;
      g_kill_reason = "";
   }
}

void UpdateKillSwitch()
{
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peak_equity)
      g_peak_equity = eq;

   double daily_loss = (g_start_day_equity - eq) / MathMax(g_start_day_equity, 1e-6);
   double drawdown = (g_peak_equity - eq) / MathMax(g_peak_equity, 1e-6);

   if(daily_loss >= InpDailyLossLimitPct)
   {
      g_killed = true;
      g_kill_reason = "DAILY_LOSS_LIMIT";
   }
   if(drawdown >= InpMaxDrawdownPct)
   {
      g_killed = true;
      g_kill_reason = "MAX_DRAWDOWN";
   }
}

bool SpreadAllowed()
{
   long spread = SymbolInfoInteger(InpSymbol, SYMBOL_SPREAD);
   if(spread > InpSpreadLimitPoints)
   {
      LogEvent("FILTER", "SPREAD");
      return false;
   }
   return true;
}

bool SessionAllowed()
{
   if(!InpEnableSessionFilter)
      return true;

   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   int h = dt.hour;
   bool london = (h >= InpLondonStartHourUTC && h < InpLondonEndHourUTC);
   bool ny = (h >= InpNewYorkStartHourUTC && h < InpNewYorkEndHourUTC);
   if(!(london || ny))
   {
      LogEvent("FILTER", "SESSION");
      return false;
   }
   return true;
}

bool IsNewsBlackout()
{
   // Stub: Use MT5 economic calendar high-impact events for production.
   // Integration: replace with CalendarValueHistory() high-impact checks.
   return false;
}

bool ReadSignal(SignalMsg &msg)
{
   int f = FileOpen(InpSignalFile, FILE_COMMON | FILE_READ | FILE_CSV | FILE_ANSI);
   if(f == INVALID_HANDLE)
      return false;

   string last_time = "";
   string last_signal = "";
   string last_conf = "";
   string last_sl = "";

   while(!FileIsEnding(f))
   {
      string t = FileReadString(f);
      if(FileIsEnding(f)) break;
      string s = FileReadString(f);
      if(FileIsEnding(f)) break;
      string c = FileReadString(f);
      if(FileIsEnding(f)) break;
      string sl = FileReadString(f);
      if(StringLen(t) == 0 || StringLen(s) == 0 || StringLen(c) == 0 || StringLen(sl) == 0)
         continue;
      if(StringLen(t) > 0)
      {
         last_time = t;
         last_signal = s;
         last_conf = c;
         last_sl = sl;
      }
   }
   FileClose(f);

   if(StringLen(last_time) == 0)
      return false;

   msg.t = (datetime)StringToTime(last_time);
   msg.signal = last_signal;
   msg.confidence = StringToDouble(last_conf);
   msg.sl_points = StringToDouble(last_sl);
   return true;
}

double ComputeRiskLot(double stop_points)
{
   if(stop_points <= 0)
      return 0.0;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money = equity * InpRiskPct;

   double tick_size = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0 || tick_value <= 0)
      return 0.0;

   double stop_value = (stop_points * _Point / tick_size) * tick_value;
   if(stop_value <= 0)
      return 0.0;

   double lots = risk_money / stop_value;
   double min_lot = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MIN);
   double step = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);

   lots = MathMax(min_lot, lots);
   lots = MathFloor(lots / step) * step;
   return NormalizeDouble(lots, 2);
}

void LogEvent(string event, string detail)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);

   string pos = "NONE";
   double price = 0.0;
   double sl = 0.0;
   double volume = 0.0;

   if(PositionSelect(InpSymbol))
   {
      pos = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      price = PositionGetDouble(POSITION_PRICE_OPEN);
      sl = PositionGetDouble(POSITION_SL);
      volume = PositionGetDouble(POSITION_VOLUME);
   }

   int f = FileOpen(InpLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_READ | FILE_ANSI);
   if(f != INVALID_HANDLE)
   {
      FileSeek(f, 0, SEEK_END);
      FileWrite(f, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), event, detail, equity, balance, pos, price, sl, volume);
      FileClose(f);
   }

   int j = FileOpen(InpJsonLogFile, FILE_COMMON | FILE_WRITE | FILE_READ | FILE_TXT | FILE_ANSI);
   if(j != INVALID_HANDLE)
   {
      FileSeek(j, 0, SEEK_END);
      string line = StringFormat(
         "{\"time\":\"%s\",\"event\":\"%s\",\"detail\":\"%s\",\"equity\":%.2f,\"balance\":%.2f,\"position\":\"%s\",\"price\":%.5f,\"sl\":%.5f,\"volume\":%.2f}\n",
         TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), event, detail, equity, balance, pos, price, sl, volume
      );
      FileWriteString(j, line);
      FileClose(j);
   }
}
