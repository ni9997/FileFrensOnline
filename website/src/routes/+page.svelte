<!-- YOU CAN DELETE EVERYTHING IN THIS PAGE -->
<script lang="ts">
	import FileInfo from '$lib/components/FileInfo/FileInfo.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<div class="container h-full mx-auto flex justify-center items-center">
	{#await data.streamed.files}
		Loading
	{:then files}
		<ul class="min-w-[50%]">
			{#each files as f}
				<FileInfo filename={f}></FileInfo>
			{/each}
		</ul>
	{:catch error}
		{error.message}
	{/await}
	<!-- {data.post.title} -->
</div>
