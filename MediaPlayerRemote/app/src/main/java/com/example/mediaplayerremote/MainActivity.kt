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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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

// Data model for Search Results
data class TorrentItem(
    val id: String?,
    val name: String,
    val info_hash: String?,
    val size_bytes: String?,
    val size_formatted: String,
    val seeders: String?,
    val leechers: String?
)

// Data model for Active Torrents (from get_qbt_list)
data class ActiveTorrentItem(
    val hash: String,
    val name: String,
    val size_bytes: Any?, // Size can be int or string depending on source
    val size_formatted: String,
    val progress: Float?,
    val state: String?,
    val seeds: Int?,
    val leechers: Int?,
    val download_speed: Int?,
    val upload_speed: Int?
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

    // We can switch between "Search Results" and "Active Torrents" view
    var viewMode by remember { mutableStateOf("search") } // "search" or "active"

    var searchList by remember { mutableStateOf<List<TorrentItem>>(emptyList()) }
    var activeList by remember { mutableStateOf<List<ActiveTorrentItem>>(emptyList()) }

    val scope = rememberCoroutineScope()

    // Dialog state for deletion
    var showDeleteDialog by remember { mutableStateOf(false) }
    var torrentToDelete by remember { mutableStateOf<ActiveTorrentItem?>(null) }

    if (showDeleteDialog && torrentToDelete != null) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            title = { Text("Delete Torrent") },
            text = { Text("Are you sure you want to delete '${torrentToDelete!!.name}'?") },
            confirmButton = {
                TextButton(
                    onClick = {
                        scope.launch {
                            try {
                                val response = sendCommand(serverIp, serverPort, "delete_torrent ${torrentToDelete!!.hash}")
                                statusMessage = response
                                // Refresh list
                                val refreshResponse = sendCommand(serverIp, serverPort, "list_torrents")
                                if (refreshResponse.startsWith("[")) {
                                    val listType = object : TypeToken<List<ActiveTorrentItem>>() {}.type
                                    activeList = Gson().fromJson(refreshResponse, listType)
                                }
                            } catch (e: Exception) {
                                statusMessage = "Error: ${e.message}"
                            }
                            showDeleteDialog = false
                            torrentToDelete = null
                        }
                    }
                ) {
                    Text("Delete")
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Button(
                onClick = { viewMode = "search" },
                modifier = Modifier.weight(1f).padding(end = 4.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (viewMode == "search") MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
                )
            ) {
                Text("Search")
            }
            Button(
                onClick = {
                    viewMode = "active"
                    scope.launch {
                        statusMessage = "Fetching active torrents..."
                        try {
                            val response = sendCommand(serverIp, serverPort, "list_torrents")
                            if (response.startsWith("[")) {
                                val listType = object : TypeToken<List<ActiveTorrentItem>>() {}.type
                                activeList = Gson().fromJson(response, listType)
                                statusMessage = "Found ${activeList.size} active torrents"
                            } else {
                                statusMessage = "Error: $response"
                                activeList = emptyList()
                            }
                        } catch (e: Exception) {
                            statusMessage = "Error: ${e.message}"
                            activeList = emptyList()
                        }
                    }
                },
                modifier = Modifier.weight(1f).padding(start = 4.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (viewMode == "active") MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
                )
            ) {
                Text("Active Torrents")
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (viewMode == "search") {
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
                                searchList = Gson().fromJson(response, listType)
                                statusMessage = "Found ${searchList.size} results"
                            } else {
                                statusMessage = "Error: $response"
                                searchList = emptyList()
                            }
                        } catch (e: Exception) {
                            statusMessage = "Error: ${e.message}"
                            searchList = emptyList()
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Search")
            }
        }

        Spacer(modifier = Modifier.height(8.dp))
        Text(text = statusMessage)
        Spacer(modifier = Modifier.height(8.dp))

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            if (viewMode == "search") {
                items(searchList) { item ->
                    TorrentItemRow(item = item, onClick = {
                        scope.launch {
                            statusMessage = "Sending download request..."
                            try {
                                val infoHash = item.info_hash ?: ""
                                val response = sendCommand(serverIp, serverPort, "download $infoHash ${item.name}")
                                statusMessage = response
                            } catch (e: Exception) {
                                statusMessage = "Error: ${e.message}"
                            }
                        }
                    })
                }
            } else {
                items(activeList) { item ->
                    ActiveTorrentItemRow(item = item, onClick = {
                        torrentToDelete = item
                        showDeleteDialog = true
                    })
                }
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
                Text(text = "S: ${item.seeders ?: "0"} / L: ${item.leechers ?: "0"}", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
fun ActiveTorrentItemRow(item: ActiveTorrentItem, onClick: () -> Unit) {
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
                Text(text = "${(item.progress?.times(100))?.toInt() ?: 0}%", style = MaterialTheme.typography.bodyMedium)
            }
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(text = "State: ${item.state}", style = MaterialTheme.typography.bodySmall)
                val dlSpeed = item.download_speed?.div(1024) ?: 0
                Text(text = "${dlSpeed} KB/s", style = MaterialTheme.typography.bodySmall)
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
