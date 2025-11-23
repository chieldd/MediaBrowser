package com.example.mediaplayerremote

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mediaplayerremote.ui.theme.MediaPlayerRemoteTheme
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.Socket

// Data model for Torrent Items
data class TorrentItem(
    val id: String,
    val name: String,
    val info_hash: String,
    val size_bytes: String,
    val size_formatted: String,
    val seeders: String,
    val leechers: String
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MediaPlayerRemoteTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    RemoteControlScreen(
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }
}

@Composable
fun RemoteControlScreen(modifier: Modifier = Modifier) {
    val serverIp = "10.243.25.213"
    val serverPort = 5000

    var query by remember { mutableStateOf("") }
    var statusMessage by remember { mutableStateOf("") }
    var torrentList by remember { mutableStateOf<List<TorrentItem>>(emptyList()) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Search Movie") },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(8.dp))
        Button(
            onClick = {
                scope.launch {
                    statusMessage = "Searching..."
                    try {
                        val response = sendCommand(serverIp, serverPort, "search $query")
                        if (response.startsWith("[")) {
                            val listType = object : TypeToken<List<TorrentItem>>() {}.type
                            torrentList = Gson().fromJson(response, listType)
                            statusMessage = "Found ${torrentList.size} results"
                        } else {
                            statusMessage = "Error: $response"
                            torrentList = emptyList()
                        }
                    } catch (e: Exception) {
                        statusMessage = "Error: ${e.message}"
                        torrentList = emptyList()
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Search")
        }

        Spacer(modifier = Modifier.height(8.dp))
        Text(text = statusMessage)
        Spacer(modifier = Modifier.height(8.dp))

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(torrentList) { item ->
                TorrentItemRow(item = item, onClick = {
                    scope.launch {
                        statusMessage = "Sending download request..."
                        try {
                            val response = sendCommand(serverIp, serverPort, "download ${item.info_hash} ${item.name}")
                            statusMessage = response
                        } catch (e: Exception) {
                            statusMessage = "Error: ${e.message}"
                        }
                    }
                })
            }
        }
    }
}

@Composable
fun TorrentItemRow(item: TorrentItem, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = item.name, style = MaterialTheme.typography.bodyLarge)
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(text = "Size: ${item.size_formatted}", style = MaterialTheme.typography.bodyMedium)
                Text(text = "S: ${item.seeders} / L: ${item.leechers}", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

suspend fun sendCommand(ip: String, port: Int, command: String): String {
    return withContext(Dispatchers.IO) {
        val socket = Socket(ip, port)
        val writer = PrintWriter(socket.getOutputStream(), true)
        val reader = BufferedReader(InputStreamReader(socket.getInputStream()))

        writer.println(command)
        val response = reader.readLine()

        socket.close()
        response ?: "Empty response"
    }
}
