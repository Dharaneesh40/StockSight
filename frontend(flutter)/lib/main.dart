import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stock Analyzer',
      theme: ThemeData(
        primarySwatch: Colors.indigo,
        fontFamily: 'Poppins',
        scaffoldBackgroundColor: const Color(0xFFF5F7FA),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.indigoAccent,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(18),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
            textStyle: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Colors.indigoAccent, width: 2),
          ),
        ),
      ),
      home: const StockPage(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class StockPage extends StatefulWidget {
  const StockPage({super.key});

  @override
  State<StockPage> createState() => _StockPageState();
}

class _StockPageState extends State<StockPage> {
  String selectedStock = '';
  Map<String, dynamic>? result;
  bool isLoading = false;
  bool isSearching = false;
  final TextEditingController searchController = TextEditingController();
  List<Map<String, dynamic>> searchSuggestions = [];
  bool showNotFound = false;

  @override
  void dispose() {
    searchController.dispose();
    super.dispose();
  }

  void clearAllData() {
    setState(() {
      searchController.clear();
      searchSuggestions = [];
      selectedStock = '';
      result = null;
      isLoading = false;
      isSearching = false;
      showNotFound = false;
    });
  }

  Future<void> searchStocks(String query) async {
    if (query.length < 2) {
      setState(() {
        searchSuggestions = [];
        isSearching = false;
        showNotFound = false;
      });
      return;
    }

    setState(() {
      isSearching = true;
      showNotFound = false;
    });

    try {
      final response = await http
          .get(
            Uri.parse(
              'https://technicalanalysisapi.onrender.com/search?q=$query',
            ),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> suggestions = json.decode(response.body);
        setState(() {
          searchSuggestions = suggestions.cast<Map<String, dynamic>>();
          isSearching = false;
          showNotFound = suggestions.isEmpty;
        });
      } else {
        setState(() {
          searchSuggestions = [];
          isSearching = false;
          showNotFound = true;
        });
      }
    } catch (e) {
      setState(() {
        searchSuggestions = [];
        isSearching = false;
        showNotFound = true;
      });
    }
  }

  Color getSignalColor(String signal) {
    switch (signal) {
      case 'Buy':
      case 'Strong Buy':
        return Colors.green;
      case 'Sell':
      case 'Strong Sell':
        return Colors.red;
      default:
        return Colors.orange;
    }
  }

  Widget buildIndicatorCard(String title, Map<String, dynamic> indicator) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: getSignalColor(
                  indicator['signal'],
                ).withAlpha((0.15 * 255).round()),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                indicator['signal'] == 'Buy'
                    ? Icons.trending_up
                    : indicator['signal'] == 'Sell'
                    ? Icons.trending_down
                    : Icons.horizontal_rule,
                color: getSignalColor(indicator['signal']),
                size: 22,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  if (title == 'RSI')
                    Text('Value: ${indicator['value']}')
                  else if (title == 'MACD')
                    Text('Histogram: ${indicator['value']}')
                  else if (title == 'Moving Average')
                    Text(
                      '50MA: ₹${indicator['short_ma']} | 200MA: ₹${indicator['long_ma']}',
                    )
                  else if (title == 'Bollinger Bands')
                    Text(
                      'Price: ₹${indicator['current']} | Upper: ₹${indicator['upper']} | Lower: ₹${indicator['lower']}',
                    )
                  else if (title == 'Volatility')
                    Text('ATR: ${indicator['value']}%'),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: getSignalColor(indicator['signal']),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(
                indicator['signal'],
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> analyzeStock() async {
    if (selectedStock.isEmpty) return;

    setState(() {
      isLoading = true;
      result = null;
    });

    try {
      final response = await http
          .post(
            Uri.parse('https://technicalanalysisapi.onrender.com/analyze'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'symbol': selectedStock}),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        setState(() {
          result = json.decode(response.body);
          isLoading = false;
        });
      } else {
        final errorData = json.decode(response.body);
        setState(() {
          result = {'error': errorData['error'] ?? 'Analysis failed'};
          isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        result = {'error': 'Connection failed: ${e.toString()}'};
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Gradient AppBar
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(60),
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF3F51B5), Color(0xFF2196F3)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 8,
                offset: Offset(0, 4),
              ),
            ],
          ),
          child: AppBar(
            title: const Text(
              'Stock Analyzer',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                letterSpacing: 1.2,
                fontSize: 22,
              ),
            ),
            backgroundColor: Colors.transparent,
            elevation: 0,
            foregroundColor: Colors.white,
            centerTitle: true,
          ),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10),
        child: Column(
          children: [
            // Search Field - clears everything on tap
            TextField(
              controller: searchController,
              onTap: clearAllData,
              onChanged: (value) {
                if (value.isNotEmpty) {
                  searchStocks(value);
                  setState(() {
                    result = null;
                    selectedStock = '';
                  });
                } else {
                  setState(() {
                    searchSuggestions = [];
                    isSearching = false;
                    showNotFound = false;
                  });
                }
              },
              style: const TextStyle(fontSize: 16),
              decoration: InputDecoration(
                labelText: 'Search Any Indian Stock',
                labelStyle: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.indigo,
                ),
                prefixIcon: const Icon(
                  Icons.search,
                  color: Colors.indigoAccent,
                ),
                suffixIcon: isSearching
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: clearAllData,
                      )
                    : null,
                helperText:
                    'Type stock name (e.g., "Reliance", "TCS", "Force")',
              ),
            ),
            const SizedBox(height: 12),

            // Search Suggestions or Not Found
            if (searchSuggestions.isNotEmpty)
              Container(
                height: 180,
                decoration: BoxDecoration(
                  color: Colors.white,
                  border: Border.all(
                    color: Colors.indigo.withAlpha((0.08 * 255).round()),
                  ),
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.indigo.withAlpha((0.07 * 255).round()),
                      blurRadius: 8,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: ListView.builder(
                  itemCount: searchSuggestions.length,
                  itemBuilder: (context, index) {
                    final stock = searchSuggestions[index];
                    return ListTile(
                      leading: const Icon(
                        Icons.trending_up,
                        color: Colors.indigo,
                      ),
                      title: Text(
                        stock['symbol'],
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Text(stock['name']),
                      onTap: () {
                        setState(() {
                          selectedStock = stock['symbol'];
                          searchController.text = stock['symbol'];
                          searchSuggestions = [];
                          showNotFound = false;
                        });
                      },
                    );
                  },
                ),
              )
            else if (showNotFound && !isSearching)
              Container(
                height: 60,
                alignment: Alignment.center,
                margin: const EdgeInsets.only(top: 10),
                decoration: BoxDecoration(
                  color: Colors.red[50],
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Text(
                  'Stock not found',
                  style: TextStyle(
                    color: Colors.red,
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                  ),
                ),
              ),

            const SizedBox(height: 18),

            // Selected Stock Display
            if (selectedStock.isNotEmpty)
              Card(
                elevation: 4,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                color: Colors.indigo[50],
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.check_circle,
                        color: Colors.green,
                        size: 26,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Selected: $selectedStock',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            const SizedBox(height: 18),

            // Analyze Button
            if (selectedStock.isNotEmpty)
              ElevatedButton.icon(
                onPressed: analyzeStock,
                icon: const Icon(Icons.analytics_outlined),
                label: const Text('Analyze Stock'),
              ),

            const SizedBox(height: 18),

            // Results Section
            Expanded(
              child: isLoading
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          CircularProgressIndicator(),
                          SizedBox(height: 16),
                          Text(
                            'Analyzing stock data...',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.indigo,
                            ),
                          ),
                        ],
                      ),
                    )
                  : result != null
                  ? result!.containsKey('error')
                        ? Card(
                            color: Colors.red[50],
                            elevation: 2,
                            margin: const EdgeInsets.symmetric(vertical: 16),
                            child: Padding(
                              padding: const EdgeInsets.all(18),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(
                                    Icons.error,
                                    color: Colors.red,
                                    size: 48,
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    result!['error'],
                                    style: const TextStyle(
                                      color: Colors.red,
                                      fontSize: 15,
                                      fontWeight: FontWeight.bold,
                                    ),
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                              ),
                            ),
                          )
                        : SingleChildScrollView(
                            child: Column(
                              children: [
                                // Stock Info
                                Card(
                                  elevation: 6,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  color: Colors.white,
                                  child: Padding(
                                    padding: const EdgeInsets.all(18),
                                    child: Column(
                                      children: [
                                        Text(
                                          result!['company_name'],
                                          style: const TextStyle(
                                            fontSize: 20,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.indigo,
                                          ),
                                          textAlign: TextAlign.center,
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          result!['stock'],
                                          style: TextStyle(
                                            fontSize: 15,
                                            color: Colors.grey[600],
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        Text(
                                          'Current Price: ₹${result!['current_price']}',
                                          style: TextStyle(
                                            fontSize: 22,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.indigo[800],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),

                                const SizedBox(height: 14),

                                // Indicators
                                const Text(
                                  'Technical Indicators',
                                  style: TextStyle(
                                    fontSize: 17,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.indigo,
                                  ),
                                ),
                                const SizedBox(height: 6),

                                buildIndicatorCard(
                                  'RSI',
                                  result!['indicators']['rsi'],
                                ),
                                buildIndicatorCard(
                                  'MACD',
                                  result!['indicators']['macd'],
                                ),
                                buildIndicatorCard(
                                  'Moving Average',
                                  result!['indicators']['moving_average'],
                                ),
                                buildIndicatorCard(
                                  'Bollinger Bands',
                                  result!['indicators']['bollinger_bands'],
                                ),
                                buildIndicatorCard(
                                  'Volatility',
                                  result!['indicators']['volatility'],
                                ),

                                const SizedBox(height: 18),

                                // Final Suggestion
                                Card(
                                  elevation: 4,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  color: getSignalColor(
                                    result!['final_suggestion'],
                                  ).withAlpha((0.12 * 255).round()),
                                  child: Padding(
                                    padding: const EdgeInsets.all(18),
                                    child: Column(
                                      children: [
                                        const Text(
                                          'Final Recommendation',
                                          style: TextStyle(
                                            fontSize: 18,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        const SizedBox(height: 10),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 18,
                                            vertical: 10,
                                          ),
                                          decoration: BoxDecoration(
                                            color: getSignalColor(
                                              result!['final_suggestion'],
                                            ),
                                            borderRadius: BorderRadius.circular(
                                              24,
                                            ),
                                          ),
                                          child: Text(
                                            result!['final_suggestion'],
                                            style: const TextStyle(
                                              color: Colors.white,
                                              fontWeight: FontWeight.bold,
                                              fontSize: 18,
                                            ),
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        Text(
                                          'Buy: ${result!['signal_summary']['buy_count']} | '
                                          'Sell: ${result!['signal_summary']['sell_count']} | '
                                          'Hold: ${result!['signal_summary']['hold_count']}',
                                          style: TextStyle(
                                            fontSize: 14,
                                            color: Colors.grey[700],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          )
                  : const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.search, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text(
                            'Search and select a stock to analyze',
                            style: TextStyle(fontSize: 16, color: Colors.grey),
                            textAlign: TextAlign.center,
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Try searching: Reliance, TCS, Force, HDFC',
                            style: TextStyle(fontSize: 14, color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
