import json
import os
import websocket
import time
import threading
from datetime import datetime

class TradingBotSimulator:
    def __init__(self, demo_api_token):
        self.api_token = demo_api_token
        self.ws = None
        self.contract_id = None
        self.is_monitoring = False
        self.should_reconnect = True
        self.profit_target = 10  # $10 profit target
        self.stop_loss = -5      # $5 stop loss
        self.position_size = 1   # $1 stake for testing
        
    def connect(self):
        """Connect to websocket (demo account only)"""
        url = "wss://ws.derivws.com/websockets/v3?app_id=1089"  # Demo app ID
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
    def on_open(self, ws):
        """Handle connection opening"""
        print(f"[{datetime.now()}] Connected to demo server")
        print("⚠️  DEMO MODE ONLY - No real money involved")
        
        # Authorize with demo token
        auth_request = {
            "authorize": self.api_token
        }
        ws.send(json.dumps(auth_request))
        
    def on_message(self, ws, message):
        """Handle incoming messages"""
        try:
            data = json.loads(message)
            self.process_message(data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Message processing error: {e}")
            
    def process_message(self, data):
        """Process different message types"""
        msg_type = data.get("msg_type")
        
        # Debug: print all messages (but hide sensitive data)
        debug_data = data.copy()
        if "authorize" in debug_data and isinstance(debug_data["authorize"], dict):
            debug_data["authorize"] = {k: v for k, v in debug_data["authorize"].items() if k != "account_list"}
        print(f"[DEBUG] Message type: {msg_type}")
        
        if msg_type == "authorize":
            self.handle_authorization(data)
        elif msg_type == "switch":
            self.handle_account_switch(data)
        elif msg_type == "proposal":
            self.handle_proposal(data)
        elif msg_type == "buy":
            self.handle_buy(data)
        elif msg_type == "proposal_open_contract":
            self.handle_contract_update(data)
        elif msg_type == "sell":
            self.handle_sell(data)
        elif "error" in data:
            self.handle_error(data)
        else:
            print(f"[DEBUG] Unhandled message type: {msg_type}")
            print(f"[DEBUG] Data: {json.dumps(data, indent=2)}")
            
    def handle_authorization(self, data):
        """Handle successful authorization"""
        if "authorize" in data:
            auth_data = data["authorize"]
            print(f"[{datetime.now()}] Authorized successfully")
            print(f"Account: {auth_data.get('email', 'Demo Account')}")
            print(f"Current Account: {auth_data.get('loginid')} ({'Virtual' if auth_data.get('is_virtual') else 'Real'})")
            
            # Check if we're on a demo account
            if not auth_data.get('is_virtual'):
                print("⚠️  You're currently on a REAL account!")
                print("Attempting to switch to demo account...")
                
                # Find the demo account
                demo_account = None
                for account in auth_data.get('account_list', []):
                    if account.get('is_virtual') == 1:
                        demo_account = account['loginid']
                        break
                
                if demo_account:
                    print(f"🔄 Switching to demo account: {demo_account}")
                    # Use the correct format for account switching
                    switch_request = {
                        "switch": demo_account
                    }
                    self.ws.send(json.dumps(switch_request))
                    return
                else:
                    print("❌ No demo account found!")
                    print("Please create a demo account at app.deriv.com")
                    self.cleanup_and_close()
                    return
            
            balance = auth_data.get('balance', 0)
            print(f"Balance: ${balance}")
            
            # Check if balance is sufficient
            if float(balance) < self.position_size:
                print("❌ Insufficient balance! You need to top up your demo account.")
                print("Go to app.deriv.com, login to your demo account, and add virtual funds.")
                self.cleanup_and_close()
                return
            
            # Wait a moment then request proposal
            threading.Timer(1.0, self.request_proposal).start()
        else:
            print("Authorization failed")
            
    def request_proposal(self):
        """Request a trading proposal"""
        print(f"[{datetime.now()}] Requesting accumulator proposal...")
        
        # Try a simpler proposal first - Rise/Fall contract
        proposal_request = {
            "proposal": 1,
            "amount": self.position_size,
            "basis": "stake",
            "contract_type": "CALL",  # Simple Rise contract
            "currency": "USD",
            "symbol": "R_100",  # Volatility 100 Index
            "duration": 5,      # 5 ticks
            "duration_unit": "t"
        }
        
        print(f"Sending proposal: {json.dumps(proposal_request, indent=2)}")
        self.ws.send(json.dumps(proposal_request))
        
    def handle_proposal(self, data):
        """Handle proposal response"""
        if "proposal" in data:
            proposal = data["proposal"]
            proposal_id = proposal["id"]
            ask_price = proposal["ask_price"]
            
            print(f"[{datetime.now()}] ✅ Proposal received")
            contract_type = proposal.get("contract_type") or proposal.get("shortcode") or "Unknown"
            print(f"Contract: {contract_type}")
            print(f"Price: ${ask_price}")
            print(f"Payout: ${proposal.get('payout', 'N/A')}")
            
            # Buy the contract
            self.buy_contract(proposal_id, ask_price)
        else:
            print("Invalid proposal response")
            
    def buy_contract(self, proposal_id, price):
        """Buy the contract"""
        print(f"[{datetime.now()}] 🚀 Buying contract...")
        
        buy_request = {
            "buy": proposal_id,
            "price": price
        }
        self.ws.send(json.dumps(buy_request))
        
    def handle_buy(self, data):
        """Handle buy response"""
        if "buy" in data:
            buy_data = data["buy"]
            self.contract_id = buy_data["contract_id"]
            
            print(f"[{datetime.now()}] ✅ Contract bought!")
            print(f"Contract ID: {self.contract_id}")
            print(f"Price: ${buy_data['buy_price']}")
            
            # Start monitoring the contract
            self.monitor_contract()
        else:
            print("Buy failed")
            
    def monitor_contract(self):
        """Start monitoring the contract"""
        print(f"[{datetime.now()}] 📊 Monitoring contract {self.contract_id}...")
        self.is_monitoring = True
        
        # Subscribe to contract updates
        subscribe_request = {
            "proposal_open_contract": 1,
            "subscribe": 1,
            "contract_id": self.contract_id
        }
        self.ws.send(json.dumps(subscribe_request))
        
    def handle_contract_update(self, data):
        """Handle contract updates"""
        if "proposal_open_contract" in data:
            contract = data["proposal_open_contract"]
            
            if contract["is_sold"]:
                self.handle_contract_closed(contract)
            else:
                self.check_exit_conditions(contract)
                
    def check_exit_conditions(self, contract):
        """Check if we should exit the position"""
        profit = float(contract["profit"])
        print(f"Current P&L: ${profit:.2f}")
        
        if profit >= self.profit_target:
            print(f"🎯 Profit target reached! Selling...")
            self.sell_contract()
        elif profit <= self.stop_loss:
            print(f"🛑 Stop loss triggered! Selling...")
            self.sell_contract()
            
    def sell_contract(self):
        """Sell the contract"""
        if self.contract_id:
            print(f"[{datetime.now()}] 💰 Selling contract...")
            
            sell_request = {
                "sell": self.contract_id
            }
            self.ws.send(json.dumps(sell_request))
            
    def handle_sell(self, data):
        """Handle sell response"""
        if "sell" in data:
            sell_data = data["sell"]
            print(f"[{datetime.now()}] ✅ Contract sold!")
            print(f"Final P&L: ${sell_data['sold_for']}")
            self.cleanup_and_close()
        else:
            print("Sell failed")
            
    def handle_contract_closed(self, contract):
        """Handle when contract is closed"""
        print(f"[{datetime.now()}] 📋 Contract closed")
        print(f"Status: {contract['status']}")
        print(f"Final P&L: ${contract['profit']}")
        self.cleanup_and_close()
        
    def handle_error(self, data):
        """Handle API errors"""
        error = data.get("error", {})
        print(f"❌ API Error: {error.get('message', 'Unknown error')}")
        print(f"Error code: {error.get('code', 'N/A')}")
        
        # Close connection on error
        self.cleanup_and_close()
        
    def on_error(self, ws, error):
        """Handle websocket errors"""
        print(f"WebSocket error: {error}")
        
    def on_close(self, ws, close_status_code=None, close_msg=None):
        """Handle connection close"""
        print(f"[{datetime.now()}] Connection closed")
        if close_status_code:
            print(f"Close code: {close_status_code}")
        if close_msg:
            print(f"Close message: {close_msg}")
        # If we didn't intentionally close, attempt reconnect
        if self.should_reconnect:
            print("Reconnecting in 2s...")
            threading.Timer(2.0, self._reconnect).start()

    def _reconnect(self):
        """Reconnect websocket and resubscribe if needed"""
        try:
            self.connect()
            # Run in background to avoid blocking timers
            threading.Thread(
                target=lambda: self.ws.run_forever(ping_interval=20, ping_timeout=10),
                daemon=True
            ).start()
            # If we were monitoring a contract, resubscribe
            if self.is_monitoring and self.contract_id:
                threading.Timer(1.0, self.monitor_contract).start()
        except Exception as e:
            print(f"Reconnect failed: {e}")
            
    def handle_account_switch(self, data):
        """Handle account switch response"""
        if "switch" in data:
            switch_data = data["switch"]
            print(f"[{datetime.now()}] ✅ Switched to account: {switch_data.get('loginid')}")
            print(f"Account Type: {'Demo' if switch_data.get('is_virtual') else 'Real'}")
            balance = switch_data.get('balance', 0)
            print(f"Balance: ${balance}")
            
            # Check if balance is sufficient
            if float(balance) < self.position_size:
                print("❌ Insufficient balance even on demo account!")
                self.cleanup_and_close()
                return
            
            # Wait a moment then request proposal
            threading.Timer(1.0, self.request_proposal).start()
        else:
            print("Account switch failed")
            
    def cleanup_and_close(self):
        """Clean up and close connection"""
        self.is_monitoring = False
        self.contract_id = None
        self.should_reconnect = False
        
        # Close connection after a short delay
        threading.Timer(2.0, lambda: self.ws.close()).start()
        
    def run(self):
        """Run the trading bot"""
        self.connect()
        # Keepalive pings reduce unexpected disconnects
        self.ws.run_forever(ping_interval=20, ping_timeout=10)

# Main execution
if __name__ == "__main__":
    print("IMPORTANT DISCLAIMERS:")
    print("1. This is for educational purposes only")
    print("2. Always use demo accounts for testing")
    print("3. Real trading involves significant financial risk")
    print("4. Consult financial professionals before live trading")
    print("5. Never risk money you can't afford to lose")
    print()
    
    print("Starting in 5 seconds...")
    time.sleep(5)
    
    print("🤖 Starting Educational Trading Bot Simulator")
    print("⚠️  This is for DEMO/EDUCATIONAL purposes only!")
    print("⚠️  Never use real money without proper testing and risk management!")
    print("-" * 60)
    
    # Prefer environment variable for safety
    DEMO_API_TOKEN = os.environ.get("DERIV_DEMO_TOKEN", "")
    if not DEMO_API_TOKEN:
        print("❌ No API token found.")
        print("Set an environment variable DERIV_DEMO_TOKEN with your DEMO token.")
        print("Example (Linux/macOS): export DERIV_DEMO_TOKEN=\"<your_demo_token>\"")
        print("Then run: python deriv_bot.py")
    else:
        bot = TradingBotSimulator(DEMO_API_TOKEN)
        bot.run()