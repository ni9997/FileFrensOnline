<script lang="ts">
    import { writable } from 'svelte/store';
    import FileInfo from '$lib/components/FileInfo/FileInfo.svelte';
    import { FileDropzone, ProgressRadial } from '@skeletonlabs/skeleton';
    import type { PageData } from './$types';

    export let data: PageData;

    let filelist: FileList;
    let upload_form: HTMLFormElement;
    let upload_url_form: HTMLFormElement;
    let progress = writable(0); // Progress in percentage
    let searchQuery = writable(''); // Search query
    let sortColumn = writable('Date'); // Default sorting column
    let sortDirection = writable('desc'); // Default sorting direction

    // Resolved files
    let files: any[] = []; // Reactive variable to store resolved files
    let filteredFiles: any[] = []; // For filtered files
    let sortedFiles: any[] = []; // For sorted files

    // Handle resolving of the streamed files
    $: if (data.streamed.files instanceof Promise) {
        data.streamed.files
            .then((resolvedFiles) => {
                files = resolvedFiles; // Assign resolved files
            })
            .catch((error) => {
                console.error('Error resolving files:', error);
                files = []; // Reset files to empty array in case of error
            });
    } else {
        files = data.streamed.files || [];
    }

    // Reactive statements for filtering and sorting
    $: filteredFiles = files.filter(file =>
        file.name.toLowerCase().includes($searchQuery.toLowerCase())
    );

    $: sortedFiles = sortFiles(filteredFiles, $sortColumn, $sortDirection);

    // Upload file logic
    async function uploadFile() {
        const file = filelist?.item(0);
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", `https://${import.meta.env.VITE_DOMAIN}/api/upload/`);
        xhr.upload.addEventListener("progress", (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progress.set(percentComplete);
            }
        });

        xhr.onload = () => {
            if (xhr.status === 200) {
                alert("Upload completed!");
                progress.set(0); // Reset progress
            } else {
                alert("Upload failed!");
            }
        };

        xhr.onerror = () => alert("Upload error!");

        xhr.send(formData);
    }

    async function uploadFileFromUrl(event: Event) {
        event.preventDefault();

        const formData = new FormData(upload_url_form);
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `https://${import.meta.env.VITE_DOMAIN}/api/upload_url/`);

        xhr.upload.addEventListener("progress", (event) => {
            if (event.lengthComputable) {
                const percentComplete = Math.min((event.loaded / event.total) * 100, 99);
                progress.set(percentComplete);
            }
        });

        xhr.onload = () => {
            if (xhr.status === 200) {
                alert("Remote upload completed!");
                progress.set(100);
            } else {
                alert("Remote upload failed!");
                progress.set(0);
            }
        };

        xhr.onerror = () => alert("Upload error!");

        xhr.send(formData);
    }

    function sortFiles(files: any[], column: string, direction: string) {
        return files.sort((a, b) => {
            const valueA = a[column.toLowerCase()];
            const valueB = b[column.toLowerCase()];

            if (column === 'date') {
                const dateA = new Date(valueA);
                const dateB = new Date(valueB);
                return direction === 'asc' ? dateA - dateB : dateB - dateA;
            } else {
                return direction === 'asc'
                    ? valueA.localeCompare(valueB)
                    : valueB.localeCompare(valueA);
            }
        });
    }
</script>

<!-- Updated Template -->
<div class="flex w-full justify-center items-center xl:max-w-[50%] mx-auto">
    <div class="flex flex-col w-full gap-4 my-4 px-4">

        <div class="flex flex-col gap-4">
            <!-- File Upload Form -->
            <form class="w-full flex flex-col gap-4" on:submit|preventDefault={uploadFile} method="post" enctype="multipart/form-data" bind:this="{upload_form}">
                <div class="flex flex-col md:flex-row items-center gap-4">
                    <div class="flex-grow">
                        <FileDropzone name="file" bind:files={filelist} />
                    </div>
                    <button type="button" on:click={uploadFile} class="btn variant-filled">UPLOAD</button>
                </div>
            </form>

            <!-- REMOTE Upload Form -->
            <form class="w-full flex flex-col gap-4" on:submit|preventDefault={uploadFileFromUrl} method="post" enctype="application/x-www-form-urlencoded" bind:this="{upload_url_form}">
                <div class="flex flex-col md:flex-row items-center gap-4">
                    <input
                        type="text"
                        name="url"
                        placeholder="Enter URL"
                        required
                        class="flex-grow px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-500 text-black"
                    />
                    <button type="submit" class="btn variant-filled">REMOTE</button>
                </div>
            </form>

            <!-- Progress Bar -->
            <div class="w-full bg-gray-200 rounded h-4 overflow-hidden">
                <div class="bg-blue-500 h-full" style="width: {$progress}%; transition: width 0.5s;"></div>
            </div>
        </div>

        <hr class="!border-t-2" />

        <!-- Search Box -->
        <div class="h-full w-full flex flex-col">
            <input
                type="text"
                class="px-3 py-2 mb-4 border rounded focus:outline-none focus:ring focus:border-blue-500 text-black"
                placeholder="Search files..."
                bind:value={$searchQuery}
            />
         <!-- Loading Progress -->
	    {#await data.streamed.files}
		<center><ProgressRadial/></center>
            {/await}
            {#if sortedFiles.length > 0}
         <!-- Content Table -->
                <table class="w-full border-collapse border border-gray-300 text-sm">
                    <thead>
                        <tr>
                            <th class="border border-gray-300 cursor-pointer" on:click={() => {
                                sortColumn.set('Name');
                                sortDirection.update(dir => $sortColumn === 'Name' ? (dir === 'asc' ? 'desc' : 'asc') : 'asc');
                            }}>
                                Name {#if $sortColumn === 'Name'}{$sortDirection === 'asc' ? '↑' : '↓'}{/if}
                            </th>
                            <th class="border border-gray-300 cursor-pointer" on:click={() => {
                                sortColumn.set('Size');
                                sortDirection.update(dir => $sortColumn === 'Size' ? (dir === 'asc' ? 'desc' : 'asc') : 'desc');
                            }}>
                                Size {#if $sortColumn === 'Size'}{$sortDirection === 'asc' ? ' ↑' : ' ↓'}{/if}
                            </th>
                            <th class="border border-gray-300 cursor-pointer" on:click={() => {
                                sortColumn.set('Date');
                                sortDirection.update(dir => $sortColumn === 'Date' ? (dir === 'asc' ? 'desc' : 'asc') : 'desc');
                            }}>
                                Date {#if $sortColumn === 'Date'}{$sortDirection === 'asc' ? '↑' : '↓'}{/if}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each sortedFiles as file}
                            <tr>
                                <td class="border border-gray-300 px-2 py-1"><FileInfo filename={file.name}></FileInfo></td>
                                <td class="border border-gray-300 px-2 py-1">{file.size}</td>
                                <td class="border border-gray-300 px-2 py-1">{file.date}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {:else}
            {/if}
        </div>
    </div>
</div>
