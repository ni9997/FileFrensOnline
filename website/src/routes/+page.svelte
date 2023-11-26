<!-- YOU CAN DELETE EVERYTHING IN THIS PAGE -->
<script lang="ts">
	import FileInfo from '$lib/components/FileInfo/FileInfo.svelte';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<div class="container h-full mx-auto flex justify-center items-center">
	{#await data.streamed.files}
		<ProgressRadial />
	{:then files}
		<ul class="xl:max-w-[50%] space-y-4 w-full m-4">
			{#each files as f}
				<FileInfo filename={f}></FileInfo>
			{/each}
		</ul>
	{:catch error}
		{error.message}
	{/await}
	<!-- {data.post.title} -->
</div>
